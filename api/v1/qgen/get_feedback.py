"""
Get feedback API endpoint.

Provides AI-generated feedback on question drafts.
"""

import logging
import os

import supabase
from fastapi import Depends, HTTPException
from google import genai
from pydantic import BaseModel

from api.v1.auth import get_supabase_client

from .models import FeedbackList

logger = logging.getLogger(__name__)


# ============================================================================
# REQUEST SCHEMA
# ============================================================================


class GetFeedbackRequest(BaseModel):
    """Request schema for get_feedback endpoint."""

    draft_id: str


# ============================================================================
# API ENDPOINT
# ============================================================================


async def get_feedback(
    request: GetFeedbackRequest,
    supabase_client: supabase.Client = Depends(get_supabase_client),
):
    """
    API endpoint to get AI-generated feedback on a question draft.

    Args:
        request: Request containing draft_id
        supabase_client: Supabase client with authentication

    Returns:
        List of feedback items with message and priority

    Raises:
        400 Bad Request: Draft has insufficient questions (< 5)
        404 Not Found: Draft not found
        500 Internal Server Error: Processing failure
    """
    logger.info(
        "Received get_feedback request",
        extra={"draft_id": request.draft_id},
    )

    # Fetch the draft and its questions from the database
    try:
        # Fetch draft to verify it exists
        draft_response = supabase_client.table("qgen_drafts").select("*").eq("id", request.draft_id).execute()

        if not draft_response.data:
            raise HTTPException(status_code=404, detail="Draft not found")

        logger.debug(
            "Fetched draft from database",
            extra={"draft_id": request.draft_id},
        )

        sections_response = (
            supabase_client.table("qgen_draft_sections").select("id").eq("qgen_draft_id", request.draft_id).execute()
        )

        section_ids = [section["id"] for section in sections_response.data]

        if section_ids:
            questions_response = (
                supabase_client.table("gen_questions")
                .select("*")
                .eq("is_in_draft", True)
                .in_("qgen_draft_section_id", section_ids)
                .execute()
            )
        else:
            questions_response.data = []

        questions = questions_response.data
        question_count = len(questions)

        logger.debug(
            "Fetched questions from draft",
            extra={
                "draft_id": request.draft_id,
                "question_count": question_count,
            },
        )

        # Validate minimum question count
        if question_count < 5:
            logger.warning(
                "Insufficient questions for feedback",
                extra={
                    "draft_id": request.draft_id,
                    "question_count": question_count,
                },
            )
            raise HTTPException(
                status_code=400,
                detail="Draft requires at least 5 questions for feedback analysis",
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(
            "Error fetching draft data",
            extra={
                "draft_id": request.draft_id,
                "error": str(e),
            },
        )
        raise HTTPException(status_code=500, detail="Internal Server Error") from e

    # Generate AI feedback using Gemini
    try:
        gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

        # Prepare analysis data
        question_types = {}
        difficulty_distribution = {"easy": 0, "medium": 0, "hard": 0}
        total_marks = 0

        for question in questions:
            # Count question types
            q_type = question.get("question_type", "unknown")
            question_types[q_type] = question_types.get(q_type, 0) + 1

            # Count difficulty levels
            difficulty = question.get("hardness_level", "medium")
            if difficulty in difficulty_distribution:
                difficulty_distribution[difficulty] += 1

            # Sum marks
            total_marks += question.get("marks", 0)

        # Build prompt for feedback generation
        # Format questions for better readability
        questions_details = []
        for idx, question in enumerate(questions, 1):
            q_text = question.get("question_text", "N/A")[:200]
            q_text_ellipsis = "..." if len(question.get("question_text", "")) > 200 else ""
            a_text = question.get("answer_text", "N/A")[:100]
            a_text_ellipsis = "..." if len(question.get("answer_text", "")) > 100 else ""
            q_detail = f"""Question {idx}:
- Type: {question.get("question_type", "N/A")}
- Difficulty: {question.get("hardness_level", "N/A")}
- Marks: {question.get("marks", "N/A")}
- Question Text: {q_text}{q_text_ellipsis}
- Answer: {a_text}{a_text_ellipsis}"""

            # Add MCQ options if present
            if question.get("question_type") == "mcq4" and question.get("option1"):
                opt1 = question.get("option1", "")[:50]
                opt2 = question.get("option2", "")[:50]
                opt3 = question.get("option3", "")[:50]
                opt4 = question.get("option4", "")[:50]
                q_detail += f"\n- Options: {opt1}, {opt2}, {opt3}, {opt4}"
            elif question.get("question_type") == "match_the_following" and question.get("match_the_following_columns"):
                q_detail += f"\n- Columns: {str(question.get('match_the_following_columns'))[:200]}"

            questions_details.append(q_detail)

        questions_text = "\n\n".join(questions_details)

        prompt = f"""Analyze the following question paper draft and provide constructive feedback.

Draft Statistics:
- Total Questions: {question_count}
- Total Marks: {total_marks}
- Question Types: {question_types}
- Difficulty Distribution: {difficulty_distribution}

Detailed Questions:
{questions_text}

Provide 4-5 specific, actionable feedback items to improve the question paper quality.
Each feedback should focus on:
- At max 2 lines in one feedback item, single line is preferable
- Balance of difficulty levels
- Distribution of question types
- Coverage of topics/concepts
- Overall paper structure
- Quality and clarity of questions

Prioritize feedback items from 1-10 (10 being most critical).
"""
        for i in range(3):
            try:
                logger.debug(
                    "Generating AI feedback",
                    extra={"draft_id": request.draft_id, "retry": i + 1},
                )
                response = await gemini_client.aio.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt,
                    config={
                        "response_mime_type": "application/json",
                        "response_schema": FeedbackList,
                    },
                )
                break
            except Exception as e:
                logger.warning(
                    "Error generating feedback",
                    extra={
                        "draft_id": request.draft_id,
                        "error": str(e),
                        "error_type": type(e).__name__,
                        "retry": i + 1,
                    },
                )
                if i == 2:
                    raise HTTPException(
                        status_code=500,
                        detail="Failed to generate feedback after multiple attempts",
                    ) from e

        feedback_list = response.parsed
        logger.info(
            "Feedback generated successfully",
            extra={
                "draft_id": request.draft_id,
                "feedback_count": len(feedback_list.feedbacks),
            },
        )

        return feedback_list

    except Exception as e:
        logger.exception(
            "Error generating feedback",
            extra={
                "draft_id": request.draft_id,
                "error": str(e),
                "error_type": type(e).__name__,
            },
        )
        raise HTTPException(status_code=500, detail="Internal Server Error") from e

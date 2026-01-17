"""
This module contains an api endpoint
to auto correct a question written in frontend
"""

import os
import logging

import supabase
from pydantic import BaseModel, Field

from google import genai
from fastapi import Depends, status, HTTPException
from fastapi.responses import Response

from api.v1.auth import get_supabase_client
from .models import AllQuestions

logger = logging.getLogger(__name__)

# ============================================================================
# SCHEMAS
# ============================================================================


class AutoCorrectedQuestion(BaseModel):
    """Wrapper for auto-corrected question from Gemini."""

    question: AllQuestions = Field(..., description="The auto-corrected question")


# ============================================================================
# PROMPT FUNCTIONS
# ============================================================================


def auto_correct_questions_prompt(gen_question: dict):
    """
    Generate prompt to auto correct a question.

    Args:
        gen_question: Dictionary containing question data

    Returns:
        Formatted prompt string
    """
    prompt = """
    You are given this question {gen_question} and it may not be in proper latex format and a organised way. 
    There may be some grammatical errors in it. Please correct it, don't change anything related to the meaning 
    of the question itself. Return the corrected question in the same format.
    """
    return prompt.format(gen_question=gen_question)


# ============================================================================
# CORE LOGIC FUNCTIONS
# ============================================================================


def auto_correct_question_logic(
    gemini_client: genai.Client,
    gen_question_data: dict,
) -> AllQuestions:
    """
    Auto-correct a question using Gemini API.

    Args:
        gemini_client: Initialized Gemini client
        gen_question_data: Dictionary containing question data

    Returns:
        Corrected question as AllQuestions type

    Raises:
        Exception: If Gemini API call fails
    """
    questions_response = gemini_client.models.generate_content(
        model="gemini-3-flash-preview",
        contents=auto_correct_questions_prompt(gen_question_data),
        config={
            "response_mime_type": "application/json",
            "response_schema": AutoCorrectedQuestion,
        },
    )

    return questions_response.parsed.question


# ============================================================================
# API ENDPOINT
# ============================================================================


async def auto_correct_question(
    gen_question_id: str,
    supabase_client: supabase.Client = Depends(get_supabase_client),
):
    """
    API endpoint to auto-correct a question written in frontend.

    Args:
        gen_question_id: UUID of the question to correct
        supabase_client: Supabase client with authentication

    Returns:
        200 OK on success
        404 Not Found if question doesn't exist
        500 Internal Server Error on failure
    """
    try:
        # Fetch the question from the database
        gen_question = (
            supabase_client.table("gen_questions")
            .select("*")
            .eq("id", gen_question_id)
            .execute()
        )

        if not gen_question.data:
            raise HTTPException(status_code=404, detail="Gen Question not found")

        gen_question_data = gen_question.data[0]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching question: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error") from e

    try:
        # Initialize Gemini client and auto-correct the question
        gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        corrected_question = auto_correct_question_logic(
            gemini_client=gemini_client,
            gen_question_data=gen_question_data,
        )

    except Exception as e:
        logger.error(f"Error auto correcting question: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error") from e

    try:
        # Update the question in the database
        update_data = corrected_question.model_dump(exclude_none=True)

        supabase_client.table("gen_questions").update(update_data).eq(
            "id", gen_question_id
        ).execute()

    except Exception as e:
        logger.error(f"Error updating question: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error") from e

    return Response(status_code=status.HTTP_200_OK)

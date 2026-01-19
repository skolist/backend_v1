"""
This module contains an api endpoint
to regenerate a new question on same concept written in frontend
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
from .utils.retry import generate_content_with_retries

logger = logging.getLogger(__name__)

# ============================================================================
# SCHEMAS
# ============================================================================


class RegeneratedQuestion(BaseModel):
    """Wrapper for regenerated question from Gemini."""

    question: AllQuestions = Field(..., description="The regenerated question")


# ============================================================================
# PROMPT FUNCTIONS
# ============================================================================


def regenerate_question_prompt(gen_question: dict):
    """
    Generate prompt to regenerate a question.

    Args:
        gen_question: Dictionary containing question data

    Returns:
        Formatted prompt string
    """
    prompt = """
    You are given this question {gen_question}. Using the same concepts in this question, generate a new question. Return the new question in the same format.
    """
    return prompt.format(gen_question=gen_question)


# ============================================================================
# CORE LOGIC FUNCTIONS
# ============================================================================


async def regenerate_question_logic(
    gemini_client: genai.Client,
    gen_question_data: dict,
    max_validation_retries: int = 5,
) -> AllQuestions:
    """
    Regenerate a question using Gemini API.

    Args:
        gemini_client: Initialized Gemini client
        gen_question_data: Dictionary containing question data
        max_validation_retries: Max retries if Pydantic validation fails

    Returns:
        Regenerated question as AllQuestions type

    Raises:
        Exception: If Gemini API call fails after all retries
    """
    last_error = None

    for attempt in range(max_validation_retries):
        try:
            questions_response = await generate_content_with_retries(
                gemini_client=gemini_client,
                model="gemini-3-flash-preview",
                contents=regenerate_question_prompt(gen_question_data),
                config={
                    "response_mime_type": "application/json",
                    "response_schema": RegeneratedQuestion,
                },
                retries=5,
            )

            # Try to parse the response - this is where Pydantic validation happens
            return questions_response.parsed.question

        except Exception as e:
            last_error = e
            # Check if it's a Pydantic validation error or parsing error
            error_str = str(e).lower()
            is_validation_error = any(
                keyword in error_str
                for keyword in [
                    "validation",
                    "field required",
                    "missing",
                    "invalid",
                    "parse",
                ]
            )

            if is_validation_error and attempt < max_validation_retries - 1:
                logger.warning(
                    f"Pydantic validation failed (attempt {attempt + 1}/{max_validation_retries}): {e}. "
                    f"Retrying with new Gemini request..."
                )
                continue
            else:
                # Not a validation error or last attempt, re-raise
                raise

    # If we exhausted all retries
    raise last_error


# ============================================================================
# API ENDPOINT
# ============================================================================


async def regenerate_question(
    gen_question_id: str,
    supabase_client: supabase.Client = Depends(get_supabase_client),
):
    """
    API endpoint to regenerate a new question on same concept written in frontend.

    Args:
        gen_question_id: UUID of the question to regenerate
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
        # Initialize Gemini client and regenerate the question
        gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        regenerated_question = await regenerate_question_logic(
            gemini_client=gemini_client,
            gen_question_data=gen_question_data,
        )

    except Exception as e:
        logger.error(f"Error regenerating question: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error") from e

    try:
        # Update the question in the database
        update_data = regenerated_question.model_dump(exclude_none=True)

        supabase_client.table("gen_questions").update(update_data).eq(
            "id", gen_question_id
        ).execute()

    except Exception as e:
        logger.error(f"Error updating question: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error") from e

    return Response(status_code=status.HTTP_200_OK)

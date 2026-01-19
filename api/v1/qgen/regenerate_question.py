"""
Regenerate question API endpoint.

Architecture:
    1. process_question() - Single Gemini call (no retries)
    2. process_question_and_validate() - Calls process_question + validates response
    3. try_retry_and_update() - Retry wrapper (5 retries) + updates Supabase
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


class RegeneratedQuestion(BaseModel):
    """Wrapper for regenerated question from Gemini."""

    question: AllQuestions = Field(..., description="The regenerated question")


# ============================================================================
# CUSTOM EXCEPTIONS
# ============================================================================


class QuestionProcessingError(Exception):
    """Raised when question processing fails after all retries."""

    pass


class QuestionValidationError(Exception):
    """Raised when question validation fails."""

    pass


# ============================================================================
# LOGGING HELPER
# ============================================================================


def _log_prefix(retry_idx: int = None) -> str:
    """
    Generate consistent log prefix with RETRY info.

    Format: "RETRY:Y |" or empty string
    """
    if retry_idx is not None:
        return f"RETRY:{retry_idx} | "
    return ""


# ============================================================================
# PROMPT FUNCTIONS
# ============================================================================


def regenerate_question_prompt(gen_question: dict) -> str:
    """
    Generate prompt to regenerate a question.

    Args:
        gen_question: Dictionary containing question data

    Returns:
        Formatted prompt string
    """
    # Using f-string to avoid issues with curly braces in LaTeX
    return f"""
    You are given this question {gen_question}. Using the same concepts in this question, generate a new question. Return the new question in the same format.
    
    Common Latex Errors are:
        1] Not placing inside $$ symbols
        Ex. If \\sin^2\\theta = \\frac{{1}}{{3}}, what is the value of \\cos^2\\theta : This is not acceptable
            If $\\sin^2\\theta = 0.6$, then $\\cos^2\\theta = \\_.$ : This is acceptable
        2] For fill in the blanks etc. spaces should use \\_\\_ not some text{{__}} wrapper
    """


# ============================================================================
# STEP 1: SINGLE QUESTION PROCESSING (No Retries)
# ============================================================================


async def process_question(
    gemini_client: genai.Client,
    gen_question_data: dict,
    retry_idx: int = None,
) -> dict:
    """
    Process a question by calling Gemini API once.

    This function makes a single API call without any retry logic.

    Args:
        gemini_client: Initialized Gemini client
        gen_question_data: Dictionary containing question data
        retry_idx: Current retry attempt number (for logging)

    Returns:
        Raw response from Gemini API

    Raises:
        QuestionProcessingError: If the API call fails
    """
    prefix = _log_prefix(retry_idx)

    logger.debug(f"{prefix}Processing regenerate for question")

    prompt = regenerate_question_prompt(gen_question_data)

    logger.debug(f"{prefix}Making Gemini API call...")

    # Single API call - no retries here
    response = await gemini_client.aio.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config={
            "response_mime_type": "application/json",
            "response_schema": RegeneratedQuestion,
        },
    )

    logger.debug(f"{prefix}Gemini API call completed successfully")

    return response


# ============================================================================
# STEP 2: QUESTION PROCESSING + VALIDATION
# ============================================================================


async def process_question_and_validate(
    gemini_client: genai.Client,
    gen_question_data: dict,
    retry_idx: int = None,
) -> AllQuestions:
    """
    Process and validate a question.

    Calls process_question() and then validates the response.

    Args:
        gemini_client: Initialized Gemini client
        gen_question_data: Dictionary containing question data
        retry_idx: Current retry attempt number (for logging)

    Returns:
        Validated AllQuestions object

    Raises:
        QuestionValidationError: If validation fails
        QuestionProcessingError: If the API call fails
    """
    prefix = _log_prefix(retry_idx)

    logger.debug(f"{prefix}Starting regenerate processing and validation")

    # Step 1: Get response from Gemini
    response = await process_question(gemini_client, gen_question_data, retry_idx)

    # Step 2: Parse and validate response
    logger.debug(f"{prefix}Parsing Gemini response...")

    try:
        regenerated_question = response.parsed.question
        logger.debug(f"{prefix}Successfully parsed regenerated question")
    except Exception as parse_error:
        logger.warning(f"{prefix}Failed to parse response: {parse_error}")
        raise QuestionValidationError(f"Failed to parse response: {parse_error}")

    # Step 3: Validate essential fields
    if not regenerated_question.question_text:
        logger.warning(f"{prefix}Regenerated question missing question_text")
        raise QuestionValidationError("Regenerated question missing question_text")

    logger.debug(f"{prefix}Question validated successfully")

    return regenerated_question


# ============================================================================
# STEP 3: RETRY WRAPPER + SUPABASE UPDATE
# ============================================================================


async def try_retry_and_update(
    gemini_client: genai.Client,
    gen_question_data: dict,
    gen_question_id: str,
    supabase_client: supabase.Client,
    max_retries: int = 5,
) -> bool:
    """
    Attempt to process question with retry logic and update Supabase.

    Wraps process_question_and_validate() with configurable retries.
    On success, updates the question in Supabase.

    Args:
        gemini_client: Initialized Gemini client
        gen_question_data: Dictionary containing question data
        gen_question_id: UUID of the question to update
        supabase_client: Supabase client for database operations
        max_retries: Maximum number of retry attempts (default: 5)

    Returns:
        True if successful

    Raises:
        QuestionProcessingError: If all retry attempts fail
    """
    logger.debug(f"Starting regenerate retry wrapper (max_retries={max_retries})")

    last_exception = None

    for attempt in range(max_retries):
        retry_idx = attempt + 1
        prefix = _log_prefix(retry_idx)

        try:
            logger.debug(f"{prefix}Starting attempt {retry_idx}/{max_retries}")

            regenerated_question = await process_question_and_validate(
                gemini_client, gen_question_data, retry_idx
            )

            logger.debug(f"{prefix}Regenerate succeeded, updating database")

            # Update the question in the database
            update_data = regenerated_question.model_dump(exclude_none=True)
            supabase_client.table("gen_questions").update(update_data).eq(
                "id", gen_question_id
            ).execute()

            logger.debug(f"{prefix}Database update completed successfully")

            return True

        except Exception as e:
            last_exception = e

            if attempt < max_retries - 1:
                logger.warning(f"{prefix}Attempt failed: {e}. Retrying...")
            else:
                logger.error(f"{prefix}All {max_retries} attempts exhausted. Last error: {e}")

    # All retries exhausted
    raise QuestionProcessingError(
        f"Regenerate failed after {max_retries} retries"
    ) from last_exception


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
    logger.debug(f"Received regenerate request for question_id={gen_question_id}")

    # Fetch the question from the database
    try:
        gen_question = (
            supabase_client.table("gen_questions")
            .select("*")
            .eq("id", gen_question_id)
            .execute()
        )

        if not gen_question.data:
            raise HTTPException(status_code=404, detail="Gen Question not found")

        gen_question_data = gen_question.data[0]
        logger.debug(f"Fetched question from database")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching question: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error") from e

    # Process and update question
    try:
        gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

        await try_retry_and_update(
            gemini_client=gemini_client,
            gen_question_data=gen_question_data,
            gen_question_id=gen_question_id,
            supabase_client=supabase_client,
            max_retries=5,
        )

        logger.debug(f"Regenerate completed successfully for question_id={gen_question_id}")

    except QuestionProcessingError as e:
        logger.error(f"Error regenerating question: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error") from e
    except Exception as e:
        logger.error(f"Unexpected error regenerating question: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error") from e

    return Response(status_code=status.HTTP_200_OK)

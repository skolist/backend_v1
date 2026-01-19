"""
Auto-correct question API endpoint.

Architecture:
    1. process_question() - Single Gemini call (no retries)
    2. process_question_and_validate() - Calls process_question + validates response
    3. try_retry_and_update() - Retry wrapper (5 retries) + updates Supabase
"""

import os
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

import supabase
from pydantic import BaseModel, Field

from google import genai
from google.genai import types
from fastapi import Depends, status, HTTPException, UploadFile, File, Form
from fastapi.responses import Response

from api.v1.auth import get_supabase_client
from .models import AllQuestions
from .prompts import auto_correct_questions_prompt

logger = logging.getLogger(__name__)

# Image logging configuration
LOG_IMAGES = os.getenv("LOG_IMAGES", "false").lower() == "true"
IMAGES_LOG_DIR = Path(__file__).parent.parent.parent.parent / "logs" / "images"

# ============================================================================
# SCHEMAS
# ============================================================================


class AutoCorrectedQuestion(BaseModel):
    """Wrapper for auto-corrected question from Gemini."""

    question: AllQuestions = Field(..., description="The auto-corrected question")


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
# HELPER FUNCTIONS
# ============================================================================


async def save_image_for_debug(
    image_content: bytes,
    gen_question_id: str,
    content_type: str,
) -> Optional[str]:
    """
    Save image to logs/images directory for debugging purposes.

    Only saves when LOG_IMAGES env var is true and logging level is DEBUG.

    Args:
        image_content: Raw image bytes
        gen_question_id: Question ID for filename
        content_type: MIME type of the image

    Returns:
        Path to saved image file, or None if not saved
    """
    if not LOG_IMAGES or logger.level > logging.DEBUG:
        return None

    try:
        # Create images log directory if it doesn't exist
        IMAGES_LOG_DIR.mkdir(parents=True, exist_ok=True)

        # Determine file extension from content type
        ext_map = {
            "image/png": ".png",
            "image/jpeg": ".jpg",
            "image/jpg": ".jpg",
            "image/gif": ".gif",
            "image/webp": ".webp",
        }
        ext = ext_map.get(content_type, ".png")

        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"auto_correct_{gen_question_id}_{timestamp}{ext}"
        filepath = IMAGES_LOG_DIR / filename

        # Save the image
        filepath.write_bytes(image_content)

        logger.debug(
            "Saved debug image",
            extra={
                "filepath": str(filepath),
                "size_bytes": len(image_content),
                "content_type": content_type,
            },
        )

        return str(filepath)

    except Exception as e:
        logger.warning(
            "Failed to save debug image",
            extra={"error": str(e)},
        )
        return None


async def process_uploaded_image(
    image: UploadFile,
    gen_question_id: str = None,
) -> Optional[types.Part]:
    """
    Process uploaded image and convert it to a Gemini Part object.

    Args:
        image: Uploaded image file
        gen_question_id: Optional question ID for debug logging

    Returns:
        Gemini Part object for the image, or None if no valid image
    """
    if not image or not image.filename or not image.size or image.size == 0:
        return None

    content = await image.read()
    content_type = image.content_type or "image/jpeg"

    # Save image for debugging if enabled
    if gen_question_id:
        await save_image_for_debug(content, gen_question_id, content_type)

    # Reset file pointer for potential re-reads
    await image.seek(0)

    return types.Part.from_bytes(
        data=content,
        mime_type=content_type,
    )


# ============================================================================
# STEP 1: SINGLE QUESTION PROCESSING (No Retries)
# ============================================================================


async def process_question(
    gemini_client: genai.Client,
    gen_question_data: dict,
    image_part: Optional[types.Part] = None,
    retry_idx: int = None,
) -> dict:
    """
    Process a question by calling Gemini API once.

    This function makes a single API call without any retry logic.

    Args:
        gemini_client: Initialized Gemini client
        gen_question_data: Dictionary containing question data
        image_part: Optional Gemini Part object for attached image
        retry_idx: Current retry attempt number (for logging)

    Returns:
        Raw response from Gemini API

    Raises:
        QuestionProcessingError: If the API call fails
    """
    prefix = _log_prefix(retry_idx)

    logger.debug(
        "Processing auto-correct for question",
        extra={"retry_idx": retry_idx},
    )

    prompt = auto_correct_questions_prompt(gen_question_data)

    # Build content parts
    contents = []

    # Add image part first (if any) so the model can reference it
    if image_part:
        logger.debug(
            "Adding image part to request",
            extra={"retry_idx": retry_idx},
        )
        contents.append(image_part)

    # Add the text prompt
    contents.append(types.Part.from_text(text=prompt))

    logger.debug(
        "Making Gemini API call",
        extra={"retry_idx": retry_idx},
    )

    # Single API call - no retries here
    response = await gemini_client.aio.models.generate_content(
        model="gemini-2.5-flash",
        contents=contents,
        config={
            "response_mime_type": "application/json",
            "response_schema": AutoCorrectedQuestion,
        },
    )

    logger.debug(
        "Gemini API call completed",
        extra={
            "retry_idx": retry_idx,
            "status": "success",
        },
    )

    return response


# ============================================================================
# STEP 2: QUESTION PROCESSING + VALIDATION
# ============================================================================


async def process_question_and_validate(
    gemini_client: genai.Client,
    gen_question_data: dict,
    image_part: Optional[types.Part] = None,
    retry_idx: int = None,
) -> AllQuestions:
    """
    Process and validate a question.

    Calls process_question() and then validates the response.

    Args:
        gemini_client: Initialized Gemini client
        gen_question_data: Dictionary containing question data
        image_part: Optional Gemini Part object for attached image
        retry_idx: Current retry attempt number (for logging)

    Returns:
        Validated AllQuestions object

    Raises:
        QuestionValidationError: If validation fails
        QuestionProcessingError: If the API call fails
    """
    prefix = _log_prefix(retry_idx)

    logger.debug(
        "Starting auto-correct processing and validation",
        extra={"retry_idx": retry_idx},
    )

    # Step 1: Get response from Gemini
    response = await process_question(
        gemini_client, gen_question_data, image_part, retry_idx
    )

    # Step 2: Parse and validate response
    logger.debug(
        "Parsing Gemini response",
        extra={"retry_idx": retry_idx},
    )

    try:
        corrected_question = response.parsed.question
        logger.debug(
            "Successfully parsed auto-corrected question",
            extra={"retry_idx": retry_idx},
        )
    except Exception as parse_error:
        logger.warning(
            "Failed to parse response",
            extra={
                "retry_idx": retry_idx,
                "error": str(parse_error),
            },
        )
        raise QuestionValidationError(f"Failed to parse response: {parse_error}")

    # Step 3: Validate essential fields
    if not corrected_question.question_text:
        logger.warning(
            "Corrected question missing question_text",
            extra={"retry_idx": retry_idx},
        )
        raise QuestionValidationError("Corrected question missing question_text")

    logger.debug(
        "Question validated successfully",
        extra={"retry_idx": retry_idx},
    )

    return corrected_question


# ============================================================================
# STEP 3: RETRY WRAPPER + SUPABASE UPDATE
# ============================================================================


async def try_retry_and_update(
    gemini_client: genai.Client,
    gen_question_data: dict,
    gen_question_id: str,
    supabase_client: supabase.Client,
    image_part: Optional[types.Part] = None,
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
        image_part: Optional Gemini Part object for attached image
        max_retries: Maximum number of retry attempts (default: 5)

    Returns:
        True if successful

    Raises:
        QuestionProcessingError: If all retry attempts fail
    """
    logger.debug(
        "Starting auto-correct retry wrapper",
        extra={"max_retries": max_retries},
    )

    last_exception = None

    for attempt in range(max_retries):
        retry_idx = attempt + 1
        prefix = _log_prefix(retry_idx)

        try:
            logger.debug(
                "Starting retry attempt",
                extra={
                    "retry_idx": retry_idx,
                    "max_retries": max_retries,
                },
            )

            corrected_question = await process_question_and_validate(
                gemini_client, gen_question_data, image_part, retry_idx
            )

            logger.debug(
                "Auto-correct succeeded, updating database",
                extra={"retry_idx": retry_idx},
            )

            # Update the question in the database
            update_data = corrected_question.model_dump(exclude_none=True)
            supabase_client.table("gen_questions").update(update_data).eq(
                "id", gen_question_id
            ).execute()

            logger.debug(
                "Database update completed successfully",
                extra={
                    "retry_idx": retry_idx,
                    "gen_question_id": gen_question_id,
                },
            )

            return True

        except Exception as e:
            last_exception = e

            if attempt < max_retries - 1:
                logger.warning(
                    "Attempt failed, retrying",
                    extra={
                        "retry_idx": retry_idx,
                        "error": str(e),
                    },
                )
            else:
                logger.error(
                    "All retry attempts exhausted",
                    extra={
                        "max_retries": max_retries,
                        "final_error": str(e),
                    },
                )

    # All retries exhausted
    raise QuestionProcessingError(
        f"Auto-correct failed after {max_retries} retries"
    ) from last_exception


# ============================================================================
# API ENDPOINT
# ============================================================================


async def auto_correct_question(
    gen_question_id: str = Form(..., description="UUID of the question to correct"),
    image: Optional[UploadFile] = File(
        default=None, description="Optional image to attach for context"
    ),
    supabase_client: supabase.Client = Depends(get_supabase_client),
):
    """
    API endpoint to auto-correct a question written in frontend.

    Args:
        gen_question_id: UUID of the question to correct
        image: Optional image file to attach for context
        supabase_client: Supabase client with authentication

    Returns:
        200 OK on success
        404 Not Found if question doesn't exist
        500 Internal Server Error on failure
    """
    logger.info(
        "Received auto-correct request",
        extra={
            "gen_question_id": gen_question_id,
            "has_image": image is not None and image.filename is not None,
        },
    )

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
        logger.debug(
            "Fetched question from database",
            extra={"gen_question_id": gen_question_id},
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(
            "Error fetching question",
            extra={
                "gen_question_id": gen_question_id,
                "error": str(e),
            },
        )
        raise HTTPException(status_code=500, detail="Internal Server Error") from e

    # Process and update question
    try:
        # Process uploaded image if provided
        image_part = None
        if image:
            logger.debug(
                "Processing uploaded image",
                extra={
                    "gen_question_id": gen_question_id,
                    "image_filename": image.filename,
                },
            )
            image_part = await process_uploaded_image(image, gen_question_id)

        gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

        await try_retry_and_update(
            gemini_client=gemini_client,
            gen_question_data=gen_question_data,
            gen_question_id=gen_question_id,
            supabase_client=supabase_client,
            image_part=image_part,
            max_retries=5,
        )

        logger.info(
            "Auto-correct completed successfully",
            extra={"gen_question_id": gen_question_id},
        )

    except QuestionProcessingError as e:
        logger.exception(
            "Error auto correcting question",
            extra={
                "gen_question_id": gen_question_id,
                "error": str(e),
            },
        )
        raise HTTPException(status_code=500, detail="Internal Server Error") from e
    except Exception as e:
        logger.exception(
            "Unexpected error auto correcting question",
            extra={
                "gen_question_id": gen_question_id,
                "error": str(e),
                "error_type": type(e).__name__,
            },
        )
        raise HTTPException(status_code=500, detail="Internal Server Error") from e

    return Response(status_code=status.HTTP_200_OK)

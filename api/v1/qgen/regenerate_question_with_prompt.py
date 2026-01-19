"""
Regenerate question with custom prompt API endpoint.

Architecture:
    1. process_question() - Single Gemini call (no retries)
    2. process_question_and_validate() - Calls process_question + validates response
    3. try_retry_and_update() - Retry wrapper (5 retries) + updates Supabase
"""

import os
import logging
from typing import Optional, List

import supabase
from pydantic import BaseModel, Field

from google import genai
from google.genai import types
from fastapi import Depends, status, HTTPException, UploadFile, File, Form
from fastapi.responses import Response

from api.v1.auth import get_supabase_client
from .models import AllQuestions

logger = logging.getLogger(__name__)

# ============================================================================
# SCHEMAS
# ============================================================================


class RegeneratedQuestionWithPrompt(BaseModel):
    """Wrapper for regenerated question from Gemini with custom prompt."""

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


def regenerate_question_with_prompt_prompt(
    gen_question: dict,
    custom_prompt: Optional[str] = None,
) -> str:
    """
    Generate prompt to regenerate a question with optional custom instructions.

    Args:
        gen_question: Dictionary containing question data
        custom_prompt: Optional custom instructions for regeneration

    Returns:
        Formatted prompt string
    """
    latex_instructions = """
    Common Latex Errors are:
        1] Not placing inside $$ symbols
        Ex. If \\sin^2\\theta = \\frac{{1}}{{3}}, what is the value of \\cos^2\\theta : This is not acceptable
            If $\\sin^2\\theta = 0.6$, then $\\cos^2\\theta = \\_.$ : This is acceptable
        2] For fill in the blanks etc. spaces should use $\\_\\_$ (contained in the $$) not some text{{__}} wrapper, also raw \\_\\_ won't work, we need $\\_\\_$
    """

    # Using f-string to avoid issues with curly braces in LaTeX
    if custom_prompt and custom_prompt.strip():
        return f"""
You are given this question: {gen_question}

The user has provided the following instructions for regenerating this question:
{custom_prompt}

Please regenerate the question according to these instructions while maintaining the same format and structure. 
If files are attached, use the content from those files to inform your regeneration.
Return the regenerated question in the same format as the original.
{latex_instructions}
"""

    # Default behavior: regenerate on similar concepts (same as regenerate_question)
    return f"""
You are given this question {gen_question}. Using the same concepts in this question, generate a new question. Return the new question in the same format.
{latex_instructions}
"""


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


async def process_uploaded_files(files: List[UploadFile]) -> List[types.Part]:
    """
    Process uploaded files and convert them to Gemini Part objects.

    Args:
        files: List of uploaded files

    Returns:
        List of Gemini Part objects for the files
    """
    parts = []

    for file in files:
        if file.filename and file.size and file.size > 0:
            content = await file.read()

            # Determine mime type
            content_type = file.content_type or "application/octet-stream"

            # Handle different file types
            if content_type.startswith("image/"):
                # Image files - encode as base64 for inline data
                parts.append(
                    types.Part.from_bytes(
                        data=content,
                        mime_type=content_type,
                    )
                )
            elif content_type in ["application/pdf"]:
                # PDF files
                parts.append(
                    types.Part.from_bytes(
                        data=content,
                        mime_type=content_type,
                    )
                )
            elif content_type.startswith("text/") or content_type in [
                "application/json",
                "application/xml",
            ]:
                # Text-based files - decode and add as text
                try:
                    text_content = content.decode("utf-8")
                    parts.append(
                        types.Part.from_text(
                            text=f"File: {file.filename}\n\n{text_content}"
                        )
                    )
                except UnicodeDecodeError:
                    # If decode fails, add as binary
                    parts.append(
                        types.Part.from_bytes(
                            data=content,
                            mime_type=content_type,
                        )
                    )
            else:
                # Other binary files - add as bytes
                parts.append(
                    types.Part.from_bytes(
                        data=content,
                        mime_type=content_type,
                    )
                )

            # Reset file pointer for potential re-reads
            await file.seek(0)

    return parts


# ============================================================================
# STEP 1: SINGLE QUESTION PROCESSING (No Retries)
# ============================================================================


async def process_question(
    gemini_client: genai.Client,
    gen_question_data: dict,
    custom_prompt: Optional[str] = None,
    file_parts: Optional[List[types.Part]] = None,
    retry_idx: int = None,
) -> dict:
    """
    Process a question by calling Gemini API once.

    This function makes a single API call without any retry logic.

    Args:
        gemini_client: Initialized Gemini client
        gen_question_data: Dictionary containing question data
        custom_prompt: Optional custom instructions for regeneration
        file_parts: Optional list of Gemini Part objects for attached files
        retry_idx: Current retry attempt number (for logging)

    Returns:
        Raw response from Gemini API

    Raises:
        QuestionProcessingError: If the API call fails
    """
    prefix = _log_prefix(retry_idx)

    logger.debug(
        "Processing regenerate with prompt for question",
        extra={"retry_idx": retry_idx},
    )

    # Build the prompt text
    prompt_text = regenerate_question_with_prompt_prompt(
        gen_question=gen_question_data,
        custom_prompt=custom_prompt,
    )

    # Build content parts
    contents = []

    # Add file parts first (if any) so the model can reference them
    if file_parts:
        logger.debug(
            "Adding file parts to request",
            extra={
                "retry_idx": retry_idx,
                "file_part_count": len(file_parts),
            },
        )
        contents.extend(file_parts)

    # Add the text prompt
    contents.append(types.Part.from_text(text=prompt_text))

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
            "response_schema": RegeneratedQuestionWithPrompt,
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
    custom_prompt: Optional[str] = None,
    file_parts: Optional[List[types.Part]] = None,
    retry_idx: int = None,
) -> AllQuestions:
    """
    Process and validate a question.

    Calls process_question() and then validates the response.

    Args:
        gemini_client: Initialized Gemini client
        gen_question_data: Dictionary containing question data
        custom_prompt: Optional custom instructions for regeneration
        file_parts: Optional list of Gemini Part objects for attached files
        retry_idx: Current retry attempt number (for logging)

    Returns:
        Validated AllQuestions object

    Raises:
        QuestionValidationError: If validation fails
        QuestionProcessingError: If the API call fails
    """
    prefix = _log_prefix(retry_idx)

    logger.debug(
        "Starting regenerate with prompt processing and validation",
        extra={"retry_idx": retry_idx},
    )

    # Step 1: Get response from Gemini
    response = await process_question(
        gemini_client, gen_question_data, custom_prompt, file_parts, retry_idx
    )

    # Step 2: Parse and validate response
    logger.debug(
        "Parsing Gemini response",
        extra={"retry_idx": retry_idx},
    )

    try:
        regenerated_question = response.parsed.question
        logger.debug(
            "Successfully parsed regenerated question",
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
    if not regenerated_question.question_text:
        logger.warning(
            "Regenerated question missing question_text",
            extra={"retry_idx": retry_idx},
        )
        raise QuestionValidationError("Regenerated question missing question_text")

    logger.debug(
        "Question validated successfully",
        extra={"retry_idx": retry_idx},
    )

    return regenerated_question


# ============================================================================
# STEP 3: RETRY WRAPPER + SUPABASE UPDATE
# ============================================================================


async def try_retry_and_update(
    gemini_client: genai.Client,
    gen_question_data: dict,
    gen_question_id: str,
    supabase_client: supabase.Client,
    custom_prompt: Optional[str] = None,
    file_parts: Optional[List[types.Part]] = None,
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
        custom_prompt: Optional custom instructions for regeneration
        file_parts: Optional list of Gemini Part objects for attached files
        max_retries: Maximum number of retry attempts (default: 5)

    Returns:
        True if successful

    Raises:
        QuestionProcessingError: If all retry attempts fail
    """
    logger.debug(
        "Starting regenerate with prompt retry wrapper",
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

            regenerated_question = await process_question_and_validate(
                gemini_client, gen_question_data, custom_prompt, file_parts, retry_idx
            )

            logger.debug(
                "Regenerate with prompt succeeded, updating database",
                extra={"retry_idx": retry_idx},
            )

            # Update the question in the database
            update_data = regenerated_question.model_dump(exclude_none=True)
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
        f"Regenerate with prompt failed after {max_retries} retries"
    ) from last_exception


# ============================================================================
# API ENDPOINT
# ============================================================================


async def regenerate_question_with_prompt(
    gen_question_id: str = Form(..., description="UUID of the question to regenerate"),
    prompt: Optional[str] = Form(None, description="Custom prompt for regeneration"),
    files: List[UploadFile] = File(default=[], description="Optional files to attach"),
    supabase_client: supabase.Client = Depends(get_supabase_client),
):
    """
    API endpoint to regenerate a question with a custom prompt and optional files.

    If no prompt or files are provided, the question will be regenerated using
    similar concepts (same behavior as the basic regenerate_question endpoint).

    Args:
        gen_question_id: UUID of the question to regenerate
        prompt: Optional custom instructions for regeneration
        files: Optional list of files to attach for context
        supabase_client: Supabase client with authentication

    Returns:
        200 OK on success
        404 Not Found if question doesn't exist
        500 Internal Server Error on failure
    """
    logger.info(
        "Received regenerate with prompt request",
        extra={
            "gen_question_id": gen_question_id,
            "has_custom_prompt": bool(prompt),
            "file_count": len(files) if files else 0,
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
        # Process uploaded files if any
        file_parts = None
        if files:
            logger.debug(
                "Processing uploaded files",
                extra={
                    "gen_question_id": gen_question_id,
                    "file_count": len(files),
                },
            )
            file_parts = await process_uploaded_files(files)

        gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

        await try_retry_and_update(
            gemini_client=gemini_client,
            gen_question_data=gen_question_data,
            gen_question_id=gen_question_id,
            supabase_client=supabase_client,
            custom_prompt=prompt,
            file_parts=file_parts,
            max_retries=5,
        )

        logger.info(
            "Regenerate with prompt completed successfully",
            extra={"gen_question_id": gen_question_id},
        )

    except QuestionProcessingError as e:
        logger.exception(
            "Error regenerating question with prompt",
            extra={
                "gen_question_id": gen_question_id,
                "error": str(e),
            },
        )
        raise HTTPException(status_code=500, detail="Internal Server Error") from e
    except Exception as e:
        logger.exception(
            "Unexpected error regenerating question with prompt",
            extra={
                "gen_question_id": gen_question_id,
                "error": str(e),
                "error_type": type(e).__name__,
            },
        )
        raise HTTPException(status_code=500, detail="Internal Server Error") from e

    return Response(status_code=status.HTTP_200_OK)

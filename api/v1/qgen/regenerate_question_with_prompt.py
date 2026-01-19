"""
This module contains an api endpoint
to regenerate a question with a custom prompt and optional files
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
    if custom_prompt and custom_prompt.strip():
        prompt = """
You are given this question: {gen_question}

The user has provided the following instructions for regenerating this question:
{custom_prompt}

Please regenerate the question according to these instructions while maintaining the same format and structure. 
If files are attached, use the content from those files to inform your regeneration.
Return the regenerated question in the same format as the original.
"""
        return prompt.format(gen_question=gen_question, custom_prompt=custom_prompt)

    # Default behavior: regenerate on similar concepts (same as regenerate_question)
    prompt = """
You are given this question {gen_question}. Using the same concepts in this question, generate a new question. Return the new question in the same format.
"""
    return prompt.format(gen_question=gen_question)


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
# CORE LOGIC FUNCTIONS
# ============================================================================


async def regenerate_question_with_prompt_logic(
    gemini_client: genai.Client,
    gen_question_data: dict,
    custom_prompt: Optional[str] = None,
    file_parts: Optional[List[types.Part]] = None,
) -> AllQuestions:
    """
    Regenerate a question using Gemini API with custom prompt and files.

    Args:
        gemini_client: Initialized Gemini client
        gen_question_data: Dictionary containing question data
        custom_prompt: Optional custom instructions for regeneration
        file_parts: Optional list of Gemini Part objects for attached files

    Returns:
        Regenerated question as AllQuestions type

    Raises:
        Exception: If Gemini API call fails
    """
    # Build the prompt text
    prompt_text = regenerate_question_with_prompt_prompt(
        gen_question=gen_question_data,
        custom_prompt=custom_prompt,
    )

    # Build content parts
    contents = []

    # Add file parts first (if any) so the model can reference them
    if file_parts:
        contents.extend(file_parts)

    # Add the text prompt
    contents.append(types.Part.from_text(text=prompt_text))

    # Generate response
    questions_response = await gemini_client.aio.models.generate_content(
        model="gemini-2.0-flash",
        contents=contents,
        config={
            "response_mime_type": "application/json",
            "response_schema": RegeneratedQuestionWithPrompt,
        },
    )

    return questions_response.parsed.question


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
        # Process uploaded files if any
        file_parts = None
        if files:
            file_parts = await process_uploaded_files(files)

        # Initialize Gemini client and regenerate the question
        gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        regenerated_question = await regenerate_question_with_prompt_logic(
            gemini_client=gemini_client,
            gen_question_data=gen_question_data,
            custom_prompt=prompt,
            file_parts=file_parts,
        )

    except Exception as e:
        logger.error(f"Error regenerating question with prompt: {e}")
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

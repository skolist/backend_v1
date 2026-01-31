"""
Regenerate question service.

Architecture:
    1. process_question() - Single Gemini call (no retries)
    2. process_question_and_validate() - Calls process_question + validates response
    3. regenerate_question() - Retry wrapper (5 retries) + updates Supabase
"""

import os
import logging

import supabase
from pydantic import BaseModel, Field
from google import genai

from api.v1.qgen.models import AllQuestions
from api.v1.qgen.prompts import regenerate_question_prompt
from supabase_dir import GenImagesInsert

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
    """Generate consistent log prefix with RETRY info."""
    if retry_idx is not None:
        return f"RETRY:{retry_idx} | "
    return ""


# ============================================================================
# SERVICE CLASS
# ============================================================================


class RegenerateService:
    @staticmethod
    async def process_question(
        gemini_client: genai.Client,
        gen_question_data: dict,
        retry_idx: int = None,
    ) -> dict:
        """
        Process a question by calling Gemini API once.
        This function makes a single API call without any retry logic.
        """
        prefix = _log_prefix(retry_idx)

        logger.debug(
            "Processing regenerate for question",
            extra={"retry_idx": retry_idx},
        )

        prompt = regenerate_question_prompt(gen_question_data)

        logger.debug(
            "Making Gemini API call",
            extra={"retry_idx": retry_idx},
        )

        response = await gemini_client.aio.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "response_schema": RegeneratedQuestion,
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

    @staticmethod
    async def process_and_validate(
        gemini_client: genai.Client,
        gen_question_data: dict,
        retry_idx: int = None,
    ) -> AllQuestions:
        """
        Process and validate a question.
        Calls process_question() and then validates the response.
        """
        prefix = _log_prefix(retry_idx)

        logger.debug(
            "Starting regenerate processing and validation",
            extra={"retry_idx": retry_idx},
        )

        response = await RegenerateService.process_question(gemini_client, gen_question_data, retry_idx)

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

    @staticmethod
    async def regenerate_question(
        gen_question_data: dict,
        gen_question_id: str,
        supabase_client: supabase.Client,
        max_retries: int = 5,
    ):
        """
        Attempt to process question with retry logic and update Supabase.
        """
        gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        
        logger.debug(
            "Starting regenerate retry wrapper",
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

                regenerated_question = await RegenerateService.process_and_validate(
                    gemini_client, gen_question_data, retry_idx
                )

                logger.debug(
                    "Regenerate succeeded, updating database",
                    extra={"retry_idx": retry_idx},
                )

                # Update the question in the database
                update_data = regenerated_question.model_dump(exclude_none=True)
                
                # Extract SVGs before updating gen_questions (svgs is not a column in gen_questions)
                svg_list = update_data.pop("svgs", None)
                
                # Map 'columns' to 'match_the_following_columns' if it exists (for match_the_following type)
                if "columns" in update_data:
                    cols = update_data.pop("columns")
                    if isinstance(cols, list):
                        dict_cols = {}
                        for col in cols:
                            if isinstance(col, dict):
                                dict_cols[col["name"]] = col["items"]
                            else:
                                dict_cols[getattr(col, 'name', '')] = getattr(col, 'items', [])
                        update_data["match_the_following_columns"] = dict_cols
                    else:
                        update_data["match_the_following_columns"] = cols
                
                supabase_client.table("gen_questions").update(update_data).eq(
                    "id", gen_question_id
                ).execute()
                
                # Insert SVGs into gen_images table if present
                if svg_list:
                    logger.debug(f"SVGs generated for question {gen_question_id}: {len(svg_list)} SVG(s) found")
                    
                    # First, delete existing SVGs for this question (to replace with new ones)
                    supabase_client.table("gen_images").delete().eq(
                        "gen_question_id", gen_question_id
                    ).execute()
                    
                    for position, svg_item in enumerate(svg_list, start=1):
                        try:
                            svg_string = svg_item.get("svg") if isinstance(svg_item, dict) else svg_item.svg
                            if svg_string:
                                gen_image = GenImagesInsert(
                                    gen_question_id=gen_question_id,
                                    svg_string=svg_string,
                                    position=position,
                                )
                                supabase_client.table("gen_images").insert(
                                    gen_image.model_dump(mode="json", exclude_none=True)
                                ).execute()
                        except Exception as svg_error:
                            logger.warning(f"Failed to insert SVG for question {gen_question_id}: {svg_error}")

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

        raise QuestionProcessingError(
            f"Regenerate failed after {max_retries} retries"
        ) from last_exception

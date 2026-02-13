import logging
import os

import supabase
from google import genai
from google.genai import types

from api.v1.qgen.models import AllQuestions, AutoCorrectedQuestion
from api.v1.qgen.prompts import auto_correct_questions_prompt
from api.v1.qgen.utils.screenshot_utils import generate_screenshot, save_image_for_debug
from api.v1.qgen.version_service import create_new_version_on_update
from supabase_dir import GenImagesInsert

logger = logging.getLogger(__name__)


class QuestionProcessingError(Exception):
    pass


class QuestionValidationError(Exception):
    pass


def _log_prefix(retry_idx: int = None) -> str:
    if retry_idx is not None:
        return f"RETRY:{retry_idx} | "
    return ""


class AutoCorrectService:
    @staticmethod
    async def process_question(
        gemini_client: genai.Client,
        gen_question_data: dict,
        image_part: types.Part | None = None,
        retry_idx: int = None,
    ) -> dict:
        prompt = auto_correct_questions_prompt(gen_question_data)
        contents = []
        if image_part:
            contents.append(image_part)
        contents.append(types.Part.from_text(text=prompt))

        response = await gemini_client.aio.models.generate_content(
            model="gemini-2.5-flash",
            contents=contents,
            config={
                "response_mime_type": "application/json",
                # Note: We need to define schema or import it.
                # For simplicity, we are using the one from models if available or simple dict
                # The prompt implies a structure.
                "response_schema": {
                    "type": "OBJECT",
                    "properties": {"question": {"type": "OBJECT"}},
                },
            },
        )
        return response

    @staticmethod
    async def process_and_validate(
        gemini_client: genai.Client,
        gen_question_data: dict,
        image_part: types.Part | None = None,
        retry_idx: int = None,
    ) -> AllQuestions:
        # Refined call with proper schema
        prompt = auto_correct_questions_prompt(gen_question_data)
        contents = []
        if image_part:
            contents.append(image_part)
        contents.append(types.Part.from_text(text=prompt))

        response = await gemini_client.aio.models.generate_content(
            model="gemini-2.5-flash",
            contents=contents,
            config={
                "response_mime_type": "application/json",
                "response_schema": AutoCorrectedQuestion,
            },
        )

        try:
            corrected_question = response.parsed.question
        except Exception as e:
            raise QuestionValidationError(f"Failed to parse response: {e}") from e

        if not corrected_question.question_text:
            raise QuestionValidationError("Corrected question missing question_text")

        return corrected_question

    @staticmethod
    async def correct_question(
        gen_question_data: dict,
        gen_question_id: str,
        supabase_client: supabase.Client,
        browser_service,
    ):
        # 1. Generate Screenshot
        logger.info(f"Generating screenshot for question {gen_question_id}")
        image_bytes = await generate_screenshot(gen_question_data, browser_service)

        # Log/Save image
        await save_image_for_debug(image_bytes, gen_question_id, "image/png")

        image_part = types.Part.from_bytes(data=image_bytes, mime_type="image/png")

        # 2. Call Gemini with Retry
        gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        max_retries = 5

        last_exception = None
        for attempt in range(max_retries):
            try:
                corrected_question = await AutoCorrectService.process_and_validate(
                    gemini_client, gen_question_data, image_part, attempt + 1
                )

                # 3. Update DB
                update_data = corrected_question.model_dump(exclude_none=True)

                # Extract SVGs before updating gen_questions
                # (svgs is not a column in gen_questions)
                svg_list = update_data.pop("svgs", None)

                # Map 'columns' to 'match_the_following_columns' if it exists
                # (for match_the_following type)
                if "columns" in update_data:
                    cols = update_data.pop("columns")
                    if isinstance(cols, list):
                        dict_cols = {}
                        for col in cols:
                            if isinstance(col, dict):
                                dict_cols[col["name"]] = col["items"]
                            else:
                                dict_cols[getattr(col, "name", "")] = getattr(col, "items", [])
                        update_data["match_the_following_columns"] = dict_cols
                    else:
                        update_data["match_the_following_columns"] = cols

                # Create new version before updating question
                create_new_version_on_update(supabase_client, gen_question_id, update_data)

                supabase_client.table("gen_questions").update(update_data).eq("id", gen_question_id).execute()

                # Insert SVGs into gen_images table if present
                if svg_list:
                    logger.debug(f"SVGs generated for question {gen_question_id}: {len(svg_list)} SVG(s) found")

                    # First, delete existing SVGs for this question (to replace with new ones)
                    supabase_client.table("gen_images").delete().eq("gen_question_id", gen_question_id).execute()

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

                return True
            except Exception as e:
                last_exception = e
                logger.warning(f"Attempt {attempt + 1} failed: {e}")

        raise QuestionProcessingError(f"Auto-correct failed after {max_retries} retries") from last_exception

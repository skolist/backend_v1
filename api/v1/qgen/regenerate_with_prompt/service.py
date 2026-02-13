import logging

import supabase
from fastapi import UploadFile
from google import genai
from google.genai import types

from api.v1.qgen.models import AllQuestions
from api.v1.qgen.prompts import regenerate_question_with_prompt_prompt
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


async def process_uploaded_files(files: list[UploadFile], gen_question_id: str = None) -> list[types.Part]:
    """
    Process uploaded files and convert them to Gemini Part objects.
    """
    parts = []
    for file in files:
        if file.filename and file.size and file.size > 0:
            content = await file.read()
            content_type = file.content_type or "application/octet-stream"

            # Log image files if logging is enabled
            if content_type.startswith("image/") and gen_question_id:
                try:
                    await save_image_for_debug(content, gen_question_id, content_type)
                except Exception as e:
                    logger.warning(f"Failed to log uploaded image {file.filename}: {e}")

            if content_type.startswith("image/") or content_type == "application/pdf":
                parts.append(types.Part.from_bytes(data=content, mime_type=content_type))
            elif content_type.startswith("text/") or content_type in [
                "application/json",
                "application/xml",
            ]:
                try:
                    text_content = content.decode("utf-8")
                    parts.append(types.Part.from_text(text=f"File: {file.filename}\n\n{text_content}"))
                except UnicodeDecodeError:
                    parts.append(types.Part.from_bytes(data=content, mime_type=content_type))
            else:
                parts.append(types.Part.from_bytes(data=content, mime_type=content_type))

            await file.seek(0)
    return parts


class RegenerateWithPromptService:
    @staticmethod
    async def process_question(
        gemini_client: genai.Client,
        gen_question_data: dict,
        custom_prompt: str | None = None,
        file_parts: list[types.Part] | None = None,
        retry_idx: int = None,
    ) -> dict:
        prefix = _log_prefix(retry_idx)
        logger.debug(f"{prefix}Processing regenerate with prompt for question")

        prompt_text = regenerate_question_with_prompt_prompt(
            gen_question=gen_question_data,
            custom_prompt=custom_prompt,
        )

        contents = []
        if file_parts:
            contents.extend(file_parts)
        contents.append(types.Part.from_text(text=prompt_text))

        # We need to define schema for regeneration result
        # Assuming AllQuestions structure wrapper similar to auto-correct
        # But wait, original code used RegeneratedQuestionWithPrompt local model.
        # We should create/use a shared model or just define schema inline if simple wrapper.
        # Let's check models.py again.
        # Ideally we should use the same pattern as AutoCorrectedQuestion.
        # I will reuse AutoCorrectedQuestion if it fits (question: AllQuestions)
        # or create a NEW one in models.py if needed.
        # RegeneratedQuestionWithPrompt had `question: AllQuestions`.
        # Exact same structure.
        # So I will reuse AutoCorrectedQuestion or better,
        # alias/create generic wrapper.
        # For now, to be consistent with previous code, let's use the same
        # wrapper structure.
        # I will assume we can reuse AutoCorrectedQuestion or I'll just use
        # the same Schema inline.
        # Actually, let's just use AutoCorrectedQuestion for now as it is
        # generic "question wrapper", OR add RegeneratedQuestion to models.py.
        # To be clean, I will use AutoCorrectedQuestion but maybe rename it
        # later to "QuestionResponse" to be generic.
        # For this refactor, I will reuse models.AutoCorrectedQuestion as the
        # schema structure is identical.

        from api.v1.qgen.models import AutoCorrectedQuestion

        response = await gemini_client.aio.models.generate_content(
            model="gemini-2.5-flash",
            contents=contents,
            config={
                "response_mime_type": "application/json",
                "response_schema": AutoCorrectedQuestion,
            },
        )
        return response

    @staticmethod
    async def process_and_validate(
        gemini_client: genai.Client,
        gen_question_data: dict,
        custom_prompt: str | None = None,
        file_parts: list[types.Part] | None = None,
        retry_idx: int = None,
    ) -> AllQuestions:
        response = await RegenerateWithPromptService.process_question(
            gemini_client, gen_question_data, custom_prompt, file_parts, retry_idx
        )

        try:
            regenerated_question = response.parsed.question
        except Exception as parse_error:
            raise QuestionValidationError(f"Failed to parse response: {parse_error}") from parse_error

        if not regenerated_question.question_text:
            raise QuestionValidationError("Regenerated question missing question_text")

        return regenerated_question

    @staticmethod
    async def regenerate_question(
        gen_question_data: dict,
        gen_question_id: str,
        supabase_client: supabase.Client,
        browser_service,
        gemini_client: genai.Client,
        custom_prompt: str | None = None,
        files: list[UploadFile] | None = None,
        is_camera_capture: bool = False,
    ):
        if files is None:
            files = []

        all_parts = []

        # 1. Generate Screenshot (ONLY if not a camera capture)
        # If it IS a camera capture, we trust the user's photo as the primary source
        # and avoid distracting the model with the "old" question screenshot.
        if not is_camera_capture:
            logger.info(f"Generating screenshot for question {gen_question_id}")
            try:
                image_bytes = await generate_screenshot(gen_question_data, browser_service)
                await save_image_for_debug(image_bytes, gen_question_id, "image/png")

                # Create image part
                screenshot_part = types.Part.from_bytes(data=image_bytes, mime_type="image/png")
                all_parts.append(screenshot_part)
            except Exception as e:
                logger.warning(f"Failed to generate screenshot: {e}")
        else:
            logger.info(f"Skipping screenshot generation for camera capture request: {gen_question_id}")

        # 2. Process Files
        file_parts = await process_uploaded_files(files, gen_question_id)
        all_parts.extend(file_parts)

        # 3. Call Gemini with Retry
        max_retries = 5
        last_exception = None

        for attempt in range(max_retries):
            try:
                regenerated_question = await RegenerateWithPromptService.process_and_validate(
                    gemini_client, gen_question_data, custom_prompt, all_parts, attempt + 1
                )

                # 4. Update DB
                update_data = regenerated_question.model_dump(exclude_none=True)

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

        raise QuestionProcessingError(f"Regeneration failed after {max_retries} retries") from last_exception

import logging
import os
from typing import Optional, List, Dict, Any

import supabase
from google import genai
from google.genai import types
from fastapi import UploadFile

from api.v1.qgen.models import AllQuestions
from api.v1.qgen.prompts import regenerate_question_with_prompt_prompt
from api.v1.qgen.utils.screenshot_utils import generate_screenshot, save_image_for_debug

logger = logging.getLogger(__name__)

class QuestionProcessingError(Exception):
    pass

class QuestionValidationError(Exception):
    pass

def _log_prefix(retry_idx: int = None) -> str:
    if retry_idx is not None:
        return f"RETRY:{retry_idx} | "
    return ""

async def process_uploaded_files(files: List[UploadFile]) -> List[types.Part]:
    """
    Process uploaded files and convert them to Gemini Part objects.
    """
    parts = []
    for file in files:
        if file.filename and file.size and file.size > 0:
            content = await file.read()
            content_type = file.content_type or "application/octet-stream"

            if content_type.startswith("image/") or content_type == "application/pdf":
                parts.append(types.Part.from_bytes(data=content, mime_type=content_type))
            elif content_type.startswith("text/") or content_type in ["application/json", "application/xml"]:
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
        custom_prompt: Optional[str] = None,
        file_parts: Optional[List[types.Part]] = None,
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
        # I will reuse AutoCorrectedQuestion if it fits (question: AllQuestions) or create a NEW one in models.py if needed.
        # RegeneratedQuestionWithPrompt had `question: AllQuestions`. Exact same structure.
        # So I will reuse AutoCorrectedQuestion or better, alias/create generic wrapper.
        # For now, to be consistent with previous code, let's use the same wrapper structure.
        # I will assume we can reuse AutoCorrectedQuestion or I'll just use the same Schema inline.
        # Actually, let's just use AutoCorrectedQuestion for now as it is generic "question wrapper", 
        # OR add RegeneratedQuestion to models.py. 
        # To be clean, I will use AutoCorrectedQuestion but maybe rename it later to "QuestionResponse" to be generic.
        # For this refactor, I will reuse models.AutoCorrectedQuestion as the schema structure is identical.
        
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
        custom_prompt: Optional[str] = None,
        file_parts: Optional[List[types.Part]] = None,
        retry_idx: int = None,
    ) -> AllQuestions:
        
        response = await RegenerateWithPromptService.process_question(
            gemini_client, gen_question_data, custom_prompt, file_parts, retry_idx
        )

        try:
            regenerated_question = response.parsed.question
        except Exception as parse_error:
            raise QuestionValidationError(f"Failed to parse response: {parse_error}")

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
        custom_prompt: Optional[str] = None,
        files: List[UploadFile] = [],
    ):
        # 1. Generate Screenshot
        logger.info(f"Generating screenshot for question {gen_question_id}")
        image_bytes = await generate_screenshot(gen_question_data, browser_service)
        await save_image_for_debug(image_bytes, gen_question_id, "image/png")
        
        # Create image part
        screenshot_part = types.Part.from_bytes(data=image_bytes, mime_type="image/png")
        
        # 2. Process Files
        file_parts = await process_uploaded_files(files)
        
        # Combine parts: Screenshot is KEY context, so add it.
        # The user asked to "add the screenshot of current question".
        all_parts = [screenshot_part] + file_parts

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
                supabase_client.table("gen_questions").update(update_data).eq(
                    "id", gen_question_id
                ).execute()
                
                return True
            except Exception as e:
                last_exception = e
                logger.warning(f"Attempt {attempt+1} failed: {e}")

        raise QuestionProcessingError(f"Regeneration failed after {max_retries} retries") from last_exception

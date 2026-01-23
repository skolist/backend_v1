import logging
import os
from dateutil.parser import isoparse
from typing import Optional, Dict, Any, List
from pathlib import Path
from datetime import datetime

import supabase
from google import genai
from google.genai import types
from fastapi import UploadFile

from api.v1.qgen.models import AllQuestions, AutoCorrectedQuestion
from api.v1.qgen.prompts import auto_correct_questions_prompt

logger = logging.getLogger(__name__)

LOG_IMAGES = os.getenv("LOG_IMAGES", "false").lower() == "true"
IMAGES_LOG_DIR = Path(__file__).parent.parent.parent.parent.parent / "logs" / "images"

class QuestionProcessingError(Exception):
    pass

class QuestionValidationError(Exception):
    pass

def _log_prefix(retry_idx: int = None) -> str:
    if retry_idx is not None:
        return f"RETRY:{retry_idx} | "
    return ""

async def save_image_for_debug(
    image_content: bytes,
    gen_question_id: str,
    content_type: str,
) -> Optional[str]:
    if not LOG_IMAGES or logger.level > logging.DEBUG:
        return None

    try:
        IMAGES_LOG_DIR.mkdir(parents=True, exist_ok=True)
        ext_map = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp"}
        ext = ext_map.get(content_type, ".png")
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"auto_correct_{gen_question_id}_{timestamp}{ext}"
        filepath = IMAGES_LOG_DIR / filename
        filepath.write_bytes(image_content)
        return str(filepath)
    except Exception as e:
        logger.warning("Failed to save debug image", extra={"error": str(e)})
        return None

async def generate_screenshot(question: Dict[str, Any], browser) -> bytes:
    """
    Generate a screenshot of the question using Playwright.
    """
    if not browser:
        raise QuestionProcessingError("Browser instance not available")

    # Reuse styles from download_pdf.py but simplified for single card
    # CSS for the paper - Synchronized with PaperPreview.tsx
    css = """
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    body { 
        font-family: 'Inter', sans-serif; 
        color: black; 
        line-height: 1.5; 
        padding: 20px; 
        margin: 0; 
        background-color: white;
        width: 600px; /* Fixed width for consistent screenshot */
    }
    
    .question-card {
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 16px;
        background: white;
    }

    .q-text { 
        font-size: 15px; 
        color: #1f2937; 
        font-weight: 500;
        margin-bottom: 8px;
    }
    
    .q-marks { 
        font-weight: 600; 
        font-size: 13px; 
        color: #6b7280; 
        margin-left: 8px; 
    }
    
    .options-grid { 
        display: grid; 
        grid-template-columns: repeat(2, 1fr); 
        gap: 8px 16px; 
        margin-top: 12px; 
    }
    
    .option { 
        display: flex; 
        gap: 8px; 
        font-size: 14px; 
        color: #4b5563;
    }
    
    .opt-label { 
        font-weight: 600; 
        color: #1f2937; 
    }
    
    .images-container {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        margin: 8px 0;
    }
    
    .q-image { 
        max-height: 200px; 
        max-width: 100%; 
        object-fit: contain; 
        border-radius: 4px;
    }
    
    .katex { font-size: 1.1em !important; }
    """

    katex_script = """
    <script>
        document.addEventListener("DOMContentLoaded", function() {
            renderMathInElement(document.body, {
                delimiters: [
                    {left: '$$', right: '$$', display: true},
                    {left: '$', right: '$', display: false},
                    {left: '\\\\(', right: '\\\\)', display: false},
                    {left: '\\\\[', right: '\\\\]', display: true}
                ],
                throwOnError : false
            });
        });
    </script>
    """

    # Build HTML content
    images_html = ""
    # Note: Using public URLs for images. If they are local blobs, this won't work directly 
    # but the assumption is they are uploaded or accessible URLs. 
    # For now, we assume simple rendering text is enough context, or existing image URLs work.
    
    # Construct Options
    options_html = ""
    if question.get("question_type") in ["mcq4", "msq4"]:
        options = [question.get(f"option{i}") for i in range(1, 5)]
        labels = ["a)", "b)", "c)", "d)"]
        options_html = '<div class="options-grid">'
        for i, opt in enumerate(options):
            if opt:
                options_html += f'<div class="option"><span class="opt-label">{labels[i]}</span> {opt}</div>'
        options_html += '</div>'

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.8/dist/katex.min.css">
        <script src="https://cdn.jsdelivr.net/npm/katex@0.16.8/dist/katex.min.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/katex@0.16.8/dist/contrib/auto-render.min.js"></script>
        <style>{css}</style>
    </head>
    <body>
        <div class="question-card" id="card">
            <div style="display: flex; justify-content: space-between;">
                <div class="q-text">{question.get('question_text', '')}</div>
                <span class="q-marks">[{question.get('marks', 1)} marks]</span>
            </div>
            {images_html}
            {options_html}
        </div>
        {katex_script}
    </body>
    </html>
    """

    context = await browser.new_context(device_scale_factor=2)
    page = await context.new_page()
    
    try:
        await page.set_content(html_content, wait_until="networkidle")
        # Select the card element to screenshot
        element = await page.query_selector("body") # or "#card"
        screenshot_bytes = await element.screenshot(type="png")
        return screenshot_bytes
    finally:
        await page.close()
        await context.close()


class AutoCorrectService:
    @staticmethod
    async def process_question(
        gemini_client: genai.Client,
        gen_question_data: dict,
        image_part: Optional[types.Part] = None,
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
                "response_schema": {"type": "OBJECT", "properties": {"question": {"type": "OBJECT"}}}, 
            },
        )
        return response

    @staticmethod
    async def process_and_validate(
        gemini_client: genai.Client,
        gen_question_data: dict,
        image_part: Optional[types.Part] = None,
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
            raise QuestionValidationError(f"Failed to parse response: {e}")

        if not corrected_question.question_text:
            raise QuestionValidationError("Corrected question missing question_text")

        return corrected_question

    @staticmethod
    async def correct_question(
        gen_question_data: dict,
        gen_question_id: str,
        supabase_client: supabase.Client,
        browser,
    ):
        # 1. Generate Screenshot
        logger.info(f"Generating screenshot for question {gen_question_id}")
        image_bytes = await generate_screenshot(gen_question_data, browser)
        
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
                # Ensure we don't overwrite ID or other immutable fields accidentally,
                # but AllQuestions model should coincide with DB structure.
                
                supabase_client.table("gen_questions").update(update_data).eq(
                    "id", gen_question_id
                ).execute()
                
                return True
            except Exception as e:
                last_exception = e
                logger.warning(f"Attempt {attempt+1} failed: {e}")
        
        raise QuestionProcessingError(f"Auto-correct failed after {max_retries} retries") from last_exception

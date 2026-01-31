
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

LOG_IMAGES = os.getenv("LOG_IMAGES", "false").lower() == "true"
IMAGES_LOG_DIR = Path(__file__).parent.parent.parent.parent.parent / "logs" / "images"

class ScreenshotError(Exception):
    pass

async def save_image_for_debug(
    image_content: bytes,
    gen_question_id: str,
    content_type: str = "image/png",
) -> Optional[str]:
    if not LOG_IMAGES or logger.level > logging.DEBUG:
        return None

    try:
        IMAGES_LOG_DIR.mkdir(parents=True, exist_ok=True)
        ext_map = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp"}
        ext = ext_map.get(content_type, ".png")
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"{gen_question_id}_{timestamp}{ext}"
        filepath = IMAGES_LOG_DIR / filename
        filepath.write_bytes(image_content)
        return str(filepath)
    except Exception as e:
        logger.warning("Failed to save debug image", extra={"error": str(e)})
        return None

async def generate_screenshot(question: Dict[str, Any], browser_service) -> bytes:
    """
    Generate a screenshot of the question using Playwright via BrowserService.
    """
    if not browser_service:
        raise ScreenshotError("Browser service instance not available")

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
    elif question.get("question_type") == "match_the_following":
        cols = question.get("match_the_following_columns") or {}
        col_names = list(cols.keys())
        if len(col_names) >= 2:
            left_col = cols[col_names[0]]
            right_col = cols[col_names[1]]
            max_rows = max(len(left_col), len(right_col))
            
            options_html = '<table class="match-table">'
            options_html += f'<tr><th style="text-align:left">{col_names[0]}</th><th style="text-align:left">{col_names[1]}</th></tr>'
            for i in range(max_rows):
                left_item = left_col[i] if i < len(left_col) else ""
                right_item = right_col[i] if i < len(right_col) else ""
                
                options_html += '<tr>'
                options_html += f'<td><div class="match-item"><span class="match-prefix">{i+1}.</span> {left_item}</div></td>'
                options_html += f'<td><div class="match-item"><span class="match-prefix">{chr(65+i)}.</span> {right_item}</div></td>'
                options_html += '</tr>'
            options_html += '</table>'
        
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

    try:
        screenshot_bytes = await browser_service.take_screenshot(
            html_content=html_content,
            selector="body",
            screenshot_options={"type": "png"},
            context_options={"device_scale_factor": 2}
        )
        return screenshot_bytes
    except Exception as e:
        logger.error(f"Error taking screenshots: {e}")
        raise ScreenshotError(f"Failed to generate screenshot: {e}")

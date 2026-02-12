import logging
import asyncio
from typing import List, Optional
from datetime import time

import supabase
from fastapi import Depends, HTTPException, Response, Request
from pydantic import BaseModel
from playwright.async_api import async_playwright

from api.v1.auth import get_supabase_client
from api.v1.qgen.utils.paper_utils import fetch_paper_data, format_duration
from api.v1.qgen.paper_layout_config import (
    get_pdf_margins,
    HEADER_MARGIN_BOTTOM,
    HEADER_LOGO_HEIGHT,
    HEADER_LOGO_MARGIN_BOTTOM,
    HEADER_TITLE_MARGIN_TOP,
    HEADER_META_MARGIN_TOP,
    HEADER_META_PADDING_Y,
    HEADER_META_GAP,
    INSTRUCTIONS_MARGIN_BOTTOM,
    INSTRUCTIONS_PADDING_BOTTOM,
    INSTRUCTIONS_TITLE_MARGIN_BOTTOM,
    INSTRUCTIONS_LIST_PADDING_LEFT,
    INSTRUCTIONS_ITEM_GAP,
    SECTION_MARGIN_TOP,
    SECTION_MARGIN_BOTTOM,
    QUESTION_MARGIN_BOTTOM,
    QUESTION_FLEX_GAP,
    OPTIONS_MARGIN_TOP,
    OPTIONS_GAP_X,
    OPTIONS_GAP_Y,
    ANSWER_MARGIN_BOTTOM,
    ANSWER_EXPLANATION_MARGIN_TOP,
)

logger = logging.getLogger(__name__)

class DownloadPdfRequest(BaseModel):
    draft_id: str
    mode: str  # "paper" or "answer"

async def download_pdf(
    download_req: DownloadPdfRequest,
    request: Request,
    supabase_client: supabase.Client = Depends(get_supabase_client),
):
    """
    API endpoint to generate and download a PDF of the question paper.
    """
    logger.info("Received download_pdf request", extra={"draft_id": download_req.draft_id, "mode": download_req.mode})

    # 1. Fetch Paper Data using shared utility
    data = await fetch_paper_data(download_req.draft_id, supabase_client)
    
    draft = data["draft"]
    sections = data["sections"]
    questions = data["questions"]
    instructions = data["instructions"]
    logo_url = data["logo_url"]
    images_map = data["images_map"]

    # 6. Generate HTML
    html_content = generate_paper_html(draft, sections, questions, instructions, logo_url, download_req.mode, images_map)

    # 7. Convert to PDF using Queue-based Browser Service
    try:
        browser_service = getattr(request.app.state, "browser_service", None)
        if not browser_service:
            logger.error("Browser service instance not found in app state")
            raise HTTPException(
                status_code=503, 
                detail="PDF generation service is currently initializing or unavailable."
            )

        pdf_bytes = await browser_service.generate_pdf(
            html_content,
            pdf_options={
                "format": "A4",
                "print_background": True,
                "margin": get_pdf_margins()
            }
        )

        filename = f"{draft.get('paper_title', 'Paper')}_{download_req.mode}.pdf"
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("PDF generation failed")
        raise HTTPException(status_code=500, detail="Failed to generate PDF") from e

def generate_paper_html(draft, sections, questions, instructions, logo_url, mode, images_map=None):
    # Get toggle values from draft (default to True for backward compatibility)
    show_logo = draft.get('is_show_logo', True)
    show_instructions = draft.get('is_show_instruction', True)
    show_explanation = draft.get('is_show_explanation_answer_key', True)
    
    # CSS for the paper - Values from paper_layout_config.py (synced with frontend index.css)
    css = """
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    body { 
        font-family: 'Times New Roman', Times, serif; 
        color: black; 
        line-height: 1.5; 
        padding: 0; 
        margin: 0; 
        -webkit-print-color-adjust: exact;
    }
    
    .page { 
        padding: 0; 
        box-sizing: border-box; 
    }
    
    .header { 
        text-align: center; 
        margin-bottom: """ + HEADER_MARGIN_BOTTOM + """; 
    }
    
    .logo { 
        height: """ + HEADER_LOGO_HEIGHT + """;
        width: auto;
        margin-bottom: """ + HEADER_LOGO_MARGIN_BOTTOM + """; 
        object-fit: contain;
    }
    
    .institute-name { 
        font-size: 24px; 
        font-weight: bold; 
        text-transform: uppercase; 
        letter-spacing: 0.025em;
        margin: 0; 
        line-height: 1.2;
    }
    
    .paper-title { 
        font-size: 20px; 
        font-weight: bold; 
        margin: """ + HEADER_TITLE_MARGIN_TOP + """ 0 0 0; 
        line-height: 1.2;
    }
    
    .meta-box { 
        border-top: 2px solid black; 
        border-bottom: 2px solid black; 
        padding: """ + HEADER_META_PADDING_Y + """ 8px; 
        margin-top: """ + HEADER_META_MARGIN_TOP + """; 
        display: flex; 
        justify-content: space-between; 
        font-weight: bold; 
        font-size: 14px; 
    }
    
    .meta-column {
        display: flex;
        flex-direction: column;
        gap: """ + HEADER_META_GAP + """;
    }
    
    .instructions { 
        margin-bottom: """ + INSTRUCTIONS_MARGIN_BOTTOM + """; 
        border-bottom: 2px solid black; 
        padding-bottom: """ + INSTRUCTIONS_PADDING_BOTTOM + """; 
    }
    
    .instructions-title { 
        font-weight: bold; 
        font-size: 14px; 
        margin-bottom: """ + INSTRUCTIONS_TITLE_MARGIN_BOTTOM + """; 
    }
    
    .instructions-list { 
        margin: 0; 
        padding-left: """ + INSTRUCTIONS_LIST_PADDING_LEFT + """; 
        font-size: 14px; 
        font-weight: 500;
        list-style-type: decimal;
    }
    
    .instructions-list li {
        padding-left: 4px;
        margin-bottom: """ + INSTRUCTIONS_ITEM_GAP + """;
    }
    
    .section-header { 
        display: flex;
        position: relative;
        justify-content: center; 
        align-items: baseline; 
        margin-top: """ + SECTION_MARGIN_TOP + """; 
        margin-bottom: """ + SECTION_MARGIN_BOTTOM + """; 
    }
    
    .section-name { 
        font-size: 18px; 
        font-weight: bold; 
        text-transform: uppercase; 
        text-decoration: underline; 
    }
    
    .section-marks { 
        position: absolute;
        right: 0;
        font-weight: bold; 
        font-size: 14px; 
    }
    
    .question { 
        margin-bottom: """ + QUESTION_MARGIN_BOTTOM + """; 
        display: flex; 
        gap: """ + QUESTION_FLEX_GAP + """; 
        page-break-inside: avoid;
    }
    
    .q-number { 
        font-weight: 600; 
        min-width: 20px; 
    }
    
    .q-content { 
        flex: 1; 
    }
    
    .q-row {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
    }
    
    .q-text { 
        font-size: 15px; 
        color: #1f2937;
    }
    
    .q-marks { 
        font-weight: 600; 
        font-size: 13px; 
        color: #6b7280;
        white-space: nowrap; 
        margin-left: 8px; 
    }
    
    .options-grid { 
        display: grid; 
        grid-template-columns: repeat(2, 1fr); 
        gap: """ + OPTIONS_GAP_Y + " " + OPTIONS_GAP_X + """; 
        margin-top: """ + OPTIONS_MARGIN_TOP + """; 
    }
    
    .option { 
        display: flex; 
        gap: 8px; 
        font-size: 15px; 
    }
    
    .opt-label { 
        font-weight: 600; 
        color: #1f2937;
    }
    
    .answer-container {
        margin-top: """ + ANSWER_MARGIN_BOTTOM + """;
        display: flex;
        gap: 4px;
    }
    
    .ans-label { 
        font-weight: 600; 
        font-size: 15px; 
    }
    
    .explanation-container {
        margin-top: """ + ANSWER_EXPLANATION_MARGIN_TOP + """;
        font-size: 15px;
    }
    
    .exp-label {
        font-weight: 600;
        text-decoration: none;
        margin-right: 4px;
    }
    
    .images-container {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        margin: 8px 0;
    }
    
    .q-image { 
        max-height: 96px; 
        max-width: 100%; 
        object-fit: contain; 
    }
    
    .q-svg {
        max-width: 100%;
        height: auto;
    }
    
    .page-break { 
        page-break-after: always; 
    }
    
    /* Katex matching */
    .katex { font-size: 1.05em !important; }
    </style>
    """

    # KaTeX Auto-render configuration script
    katex_script = """
    <script>
        document.addEventListener("DOMContentLoaded", function() {
            renderMathInElement(document.body, {
                delimiters: [
                    {left: '$$', right: '$$', display: true},
                    {left: '$', right: '$', display: false},
                    {left: '\\\\(', right: '\\\\)', display: false},
                    {left: '\\\\( ', right: ' \\\\)', display: false},
                    {left: '\\\\(  ', right: '  \\\\)', display: false},
                    {left: '\\\\[', right: '\\\\]', display: true}
                ],
                throwOnError : false
            });
        });
    </script>
    """

    html = f"""
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
        <div class="page">
            <div class="header">
                {f'<img src="{logo_url}" class="logo">' if show_logo and logo_url else ''}
                <div class="institute-name">{draft.get('institute_name') or 'Institute Name'}</div>
                <div class="paper-title">{draft.get('paper_title') or 'Examination Paper'}{" - Answer Key" if mode == "answer" else ""}</div>
                
                <div class="meta-box">
                    <div class="meta-column" style="text-align: left;">
                        <span>Subject: {draft.get('subject_name') or '...................'}</span>
                        <span>Class: {draft.get('school_class_name') or '...................'}</span>
                    </div>
                    <div class="meta-column" style="text-align: right;">
                        <span>Max. Marks: {draft.get('maximum_marks') or '...'}</span>
                        <span>Duration: {format_duration(draft.get('paper_duration'))}</span>
                    </div>
                </div>
            </div>

            {f'''
            <div class="instructions">
                <div class="instructions-title">General Instructions:</div>
                <ol class="instructions-list">
                    {''.join(f"<li>{inst.get('instruction_text')}</li>" for inst in instructions)}
                </ol>
            </div>
            ''' if mode == "paper" and show_instructions and instructions else ""}

            {"".join(render_section(s, questions, mode, images_map, show_explanation) for s in sections)}
        </div>
        {katex_script}
    </body>
    </html>
    """
    return html

def render_section(section, all_questions, mode, images_map=None, show_explanation=True):
    section_questions = sorted(
        [q for q in all_questions if q["qgen_draft_section_id"] == section["id"]],
        key=lambda q: q.get("position_in_draft", 0)
    )
    if not section_questions:
        return ""

    total_marks = sum(q.get("marks", 0) for q in section_questions)
    
    html = f"""
    <div class="section-container">
        <div class="section-header">
            <span class="section-name">{section.get('section_name')}</span>
            <span class="section-marks">[{total_marks}]</span>
        </div>
        {"".join(render_question(q, idx + 1, mode, images_map.get(q["id"], []) if images_map else [], show_explanation) for idx, q in enumerate(section_questions))}
    </div>
    """
    return html

def render_question(q, display_idx, mode, images=None, show_explanation=True):
    is_mcq = q.get("question_type") in ["mcq4", "msq4"]
    
    # Images rendering
    images_html = ""
    if images:
        images_html = '<div class="images-container">'
        for img in images:
            if img.get("svg_string"):
                images_html += f'<div class="q-svg">{img["svg_string"]}</div>'
            elif img.get("img_url"):
                images_html += f'<img src="{img["img_url"]}" class="q-image">'
        images_html += '</div>'

    # Options rendering
    options_html = ""
    if mode == "paper":
        if is_mcq:
            options = [q.get("option1"), q.get("option2"), q.get("option3"), q.get("option4")]
            options_html = '<div class="options-grid">'
            labels = ["a)", "b)", "c)", "d)"]
            for i, opt in enumerate(options):
                if opt:
                    options_html += f'<div class="option"><span class="opt-label">{labels[i]}</span> {opt}</div>'
            options_html += '</div>'
        elif q.get("question_type") == "match_the_following":
            cols = q.get("match_the_following_columns") or {}
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

    # Answer rendering
    answer_html = ""
    if mode == "answer":
        answer_text = q.get("answer_text") or "N/A"
        explanation_html = ""
        if show_explanation and q.get("explanation"):
            explanation_html = f'<div class="explanation-container"><span class="exp-label">Explanation:</span><span class="q-text">{q["explanation"]}</span></div>'
        answer_html = f'''
        <div class="answer-container">
            <span class="ans-label">Ans:</span> <span class="q-text">{answer_text}</span>
        </div>
        {explanation_html}
        '''

    # Break logic
    page_break = '<div class="page-break"></div>' if q.get("is_page_break_below") else ""

    html = f"""
    <div class="question">
        <div class="q-number">{display_idx}.</div>
        <div class="q-content">
            <div class="q-row">
                <div class="q-text">{q.get('question_text')}</div>
                <div class="q-marks">[{q.get('marks')}]</div>
            </div>
            {images_html}
            {options_html}
            {answer_html}
        </div>
    </div>
    {page_break}
    """
    return html

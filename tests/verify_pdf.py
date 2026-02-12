import asyncio
import os
import sys
from datetime import time

# Add the backend directory to sys.path so we can import our new module
sys.path.append(os.path.join(os.getcwd(), "backend"))

# Import the generation functions
# We need to handle the potential import error if renamed or moved
try:
    from playwright.async_api import async_playwright

    from api.v1.qgen.download_pdf import generate_paper_html
except ImportError as e:
    print(f"Error importing modules: {e}")
    sys.exit(1)

# Dummy Data for testing
DUMMY_DRAFT = {
    "institute_name": "Antigravity Research Institute",
    "paper_title": "Advanced Quantum Mechanics",
    "subject_name": "Physics",
    "school_class_name": "Class XII",
    "maximum_marks": 100,
    "paper_duration": time(hour=3, minute=0),
    "logo_url": None,
}

DUMMY_SECTIONS = [
    {"id": "sec-1", "section_name": "Section A: Theory", "position_in_draft": 1},
    {"id": "sec-2", "section_name": "Section B: Problems", "position_in_draft": 2},
]

DUMMY_INSTRUCTIONS = [
    {"instruction_text": "All questions are compulsory."},
    {"instruction_text": "Use of scientific calculator is permitted."},
    {"instruction_text": "Draw neat diagrams wherever necessary."},
]

DUMMY_QUESTIONS = [
    {
        "id": "q-1",
        "qgen_draft_section_id": "sec-1",
        "position_in_draft": 1,
        "question_text": "If $\\sin^2\\theta = 0.5$, what is the value of $\\cos^2\\theta$?",
        "marks": 1,
        "question_type": "mcq4",
        "option1": "0.25",
        "option2": "0.5",
        "option3": "0.75",
        "option4": "1.0",
        "answer_text": "0.5",
        "explanation": "Using the identity $\\sin^2\\theta + \\cos^2\\theta = 1$.",
        "is_page_break_below": False,
    },
    {
        "id": "q-2",
        "qgen_draft_section_id": "sec-1",
        "position_in_draft": 2,
        "question_text": "Identify the logic gate represented by the symbol below and explain its function.",
        "marks": 5,
        "question_type": "short_answer",
        "answer_text": "The symbol represents an AND gate.",
        "explanation": "An AND gate outputs 1 only if both inputs are 1.",
        "is_page_break_below": False,
    },
    {
        "id": "q-3",
        "qgen_draft_section_id": "sec-2",
        "position_in_draft": 3,
        "question_text": "Which of the following represents the Schrödinger equation?",
        "marks": 2,
        "question_type": "mcq4",
        "option1": "F = ma",
        "option2": "E = mc^2",
        "option3": "$H\\psi = E\\psi$",
        "option4": "PV = nRT",
        "answer_text": "Option C",
        "explanation": "The time-independent Schrödinger equation.",
        "is_page_break_below": False,
    },
]

DUMMY_IMAGES = {
    "q-2": [
        {
            "svg_string": '<svg width="100" height="50"><rect width="100" height="50" style="fill:rgb(0,0,255);stroke-width:3;stroke:rgb(0,0,0)" /><text x="25" y="30" fill="white">AND GATE</text></svg>',
            "position": 1,
            "gen_question_id": "q-2",
        },
        {
            "img_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/64/AND_ANSI.svg/200px-AND_ANSI.svg.png",
            "position": 2,
            "gen_question_id": "q-2",
        },
    ]
}


async def run_test():
    print("Starting PDF Generation Test...")

    async with async_playwright() as p:
        print("Launching headless browser...")
        browser = await p.chromium.launch(headless=True)

        # 1. Generate Question Paper PDF
        print("Generating Question Paper...")
        html_paper = generate_paper_html(
            DUMMY_DRAFT,
            DUMMY_SECTIONS,
            DUMMY_QUESTIONS,
            DUMMY_INSTRUCTIONS,
            None,
            "paper",
            DUMMY_IMAGES,
        )
        page = await browser.new_page()
        await page.set_content(html_paper, wait_until="networkidle")
        pdf_bytes_paper = await page.pdf(
            format="A4",
            print_background=True,
            margin={"top": "20mm", "bottom": "20mm", "left": "20mm", "right": "20mm"},
        )
        with open("test_paper_preview.pdf", "wb") as f:
            f.write(pdf_bytes_paper)
        await page.close()

        # 2. Generate Answer Key PDF
        print("Generating Answer Key...")
        html_answer = generate_paper_html(
            DUMMY_DRAFT,
            DUMMY_SECTIONS,
            DUMMY_QUESTIONS,
            DUMMY_INSTRUCTIONS,
            None,
            "answer",
            DUMMY_IMAGES,
        )
        page = await browser.new_page()
        await page.set_content(html_answer, wait_until="networkidle")
        pdf_bytes_answer = await page.pdf(
            format="A4",
            print_background=True,
            margin={"top": "20mm", "bottom": "20mm", "left": "20mm", "right": "20mm"},
        )
        with open("test_answer_preview.pdf", "wb") as f:
            f.write(pdf_bytes_answer)
        await page.close()

        await browser.close()

    print("Success! PDFs generated:")
    print(f" - Paper: {os.path.abspath('test_paper_preview.pdf')}")
    print(f" - Answer: {os.path.abspath('test_answer_preview.pdf')}")
    print("You can now open these files to manually verify the layout, LaTeX, and styling.")


if __name__ == "__main__":
    asyncio.run(run_test())

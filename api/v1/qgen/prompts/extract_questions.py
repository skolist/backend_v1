"""
Prompt template for extracting questions from files (images/PDFs).
"""

from typing import Optional

from .common_instructions import COMMON_INSTRUCTIONS
from .svg_instructions import COMMON_SVG_INSTRUCTIONS


def extract_questions_prompt(custom_prompt: Optional[str] = None) -> str:
    """
    Generate prompt to extract questions from a file.

    Args:
        custom_prompt: Optional custom instructions for extraction

    Returns:
        Formatted prompt string
    """
    base_prompt = f"""
Analyze the attached file (image or PDF) and extract ALL questions found in it.

For each question, determine its type from one of these categories:
- mcq4: Multiple choice with 4 options, single correct answer
- msq4: Multiple select with 4 options, one or more correct answers
- fill_in_the_blank: Fill in the blank question
- true_false: True or False statement
- short_answer: Short answer question
- long_answer: Long answer/essay question

For each question, extract:
1. The complete question text (preserve any LaTeX/math notation) (Don't unnecessarily use double $$...$$, if inline is required use single $...$)
2. Options (if applicable for MCQ/MSQ)
3. Correct answer(s) - for MCQ4 use correct_mcq_option (1-4), for MSQ4 use msq_option1_answer to msq_option4_answer
4. Answer text (for non-MCQ types)
5. Explanation if visible
6. Difficulty level if determinable (easy, medium, hard)
7. Marks if specified

IMPORTANT LaTeX handling instructions:
{COMMON_INSTRUCTIONS}

If diagrams are part of questions, generate SVG following these instructions:
{COMMON_SVG_INSTRUCTIONS}

Extract questions exactly as they appear. Do not modify or paraphrase the question content.
If a question has sub-parts, treat each sub-part as a separate question.
"""

    if custom_prompt and custom_prompt.strip():
        return f"{base_prompt}\n\nAdditional Instructions from user:\n{custom_prompt}"
    
    return base_prompt

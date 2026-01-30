"""
Prompt template for auto-correcting questions.
"""

from .common_instructions import COMMON_INSTRUCTIONS
from .svg_instructions import COMMON_SVG_INSTRUCTIONS

def auto_correct_questions_prompt(gen_question: dict) -> str:
    """
    Generate prompt to auto correct a question.

    Args:
        gen_question: Dictionary containing question data

    Returns:
        Formatted prompt string
    """
    # Using f-string instead of .format() to avoid issues with curly braces in LaTeX
    return f"""
    You are given this question {gen_question} and it may not be in proper latex format and a organised way. 
    There may be some grammatical errors in it. Please correct it, don't change anything related to the meaning 
    of the question itself. Return the corrected question in the same format.
    If user has requested something, then there must be something like either grammatical or latex error. High probability that it is latex error in maths question, so check the question carefully.
    If an image is attached, use it to help understand and correct the question content.
    If Diagram is/are required for the questions, then generate it following the below SVG Instructions.
    Common Latex Errors are:
        {COMMON_INSTRUCTIONS}
    Svg Instructions are:
        {COMMON_SVG_INSTRUCTIONS}
    Correct everything , the image would inlude the question text, answer text, options etc. if there are any latex / katex rendering errors , you can check from image if image is attached. Use this image as source of truth, your output is rendered as that image, do necessary actions if there are any katex errors (we are using katex node module at the frontend to render your image)
    """

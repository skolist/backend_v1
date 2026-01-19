"""
Prompt template for regenerating questions.
"""

from .common_instructions import COMMON_INSTRUCTIONS

def regenerate_question_prompt(gen_question: dict) -> str:
    """
    Generate prompt to regenerate a question.

    Args:
        gen_question: Dictionary containing question data

    Returns:
        Formatted prompt string
    """
    # Using f-string to avoid issues with curly braces in LaTeX
    return f"""
    You are given this question {gen_question}. Using the same concepts in this question, generate a new question. Return the new question in the same format.
    
    Common Latex Errors are:
        {COMMON_INSTRUCTIONS}
    """

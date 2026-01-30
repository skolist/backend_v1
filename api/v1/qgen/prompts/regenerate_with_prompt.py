"""
Prompt template for regenerating questions with custom prompt.
"""

from typing import Optional

from .common_instructions import COMMON_INSTRUCTIONS
from .svg_instructions import COMMON_SVG_INSTRUCTIONS

def regenerate_question_with_prompt_prompt(
    gen_question: dict,
    custom_prompt: Optional[str] = None,
) -> str:
    """
    Generate prompt to regenerate a question with optional custom instructions.

    Args:
        gen_question: Dictionary containing question data
        custom_prompt: Optional custom instructions for regeneration

    Returns:
        Formatted prompt string
    """

    # Using f-string to avoid issues with curly braces in LaTeX
    if custom_prompt and custom_prompt.strip():
        return f"""
You are given this question: {gen_question}

A screenshot of the current question is attached for reference if you need to understand the visual layout or specific rendering details.

The user has provided the following instructions for regenerating this question:
{custom_prompt}

Please regenerate the question according to these instructions while maintaining the same format and structure. 
If files are attached, use the content from those files to inform your regeneration.
Return the regenerated question in the same format as the original.
Common Latex Errors:
    {COMMON_INSTRUCTIONS}

If Diagram is/are required for the questions, then generate it following the below SVG Instructions.
Svg Instructions are:
    {COMMON_SVG_INSTRUCTIONS}
"""

    # Default behavior: regenerate on similar concepts (same as regenerate_question)
    return f"""
You are given this question {gen_question}. A screenshot of the current question is attached for reference. Using the same concepts in this question, generate a new question. Return the new question in the same format.
Common Latex Errors:
    {COMMON_INSTRUCTIONS}

If Diagram is/are required for the questions, then generate it following the below SVG Instructions.
Svg Instructions are:
    {COMMON_SVG_INSTRUCTIONS}
"""

"""
Prompt template for generating questions with granular concept association.
"""

from typing import List, Dict, Optional
from .common_instructions import COMMON_INSTRUCTIONS
from .svg_instructions import COMMON_SVG_INSTRUCTIONS

def generate_questions_with_concepts_prompt(
    concepts: List[str],
    concepts_descriptions: Dict[str, str],
    old_questions_on_concepts: list,
    n: int,
    question_type: str,
    difficulty: str,
    instructions: Optional[str] = None,
) -> str:
    """
    Generate prompt for creating questions for a batch of concepts.
    Instructs Gemini to associate specific concepts with each question.
    """
    # Build concept information
    concept_info = []
    for concept in concepts:
        desc = concepts_descriptions.get(concept, "No description available")
        concept_info.append(f"{concept}: {desc}")

    concepts_text = "\n".join(concept_info)

    instructions_block = (
        f"IMPORTANT CUSTOM INSTRUCTIONS:\n{instructions}\n(PRIORITIZE THESE ABOVE EVERYTHING ELSE)\n"
        if instructions
        else ""
    )

    return f"""
    {instructions_block}

    You have access to these concepts and their descriptions:
    {concepts_text}
    
    Historical questions for reference: {old_questions_on_concepts}
    
    Generate {n} questions of type {question_type} with difficulty level: {difficulty}
    
    Instructions:
    - For EACH question, identify which specific concepts from the provided list are directly relevant and include them in the 'concepts' field as a list of concept names.
    - Each question MUST be associated with at least one concept from the provided list.
    - The questions should align with the specified difficulty level: {difficulty}
    - Use patterns from historical questions as reference but create original questions
    - Be strictly within the knowledge of the provided concepts, unless custom instructions above contradict this.
    - Strictly use LaTeX format for mathematical entities like symbols and formulas
    - Strictly output all required fields for the question schema. Answer Text is mandatory, use LaTeX where needed
    - Question should be Strictly Accurate and High Quality

    Common Latex Errors are:
        {COMMON_INSTRUCTIONS}

    If Diagram is/are required for the questions, then generate it following the below SVG Instructions.
    Svg Instructions are:
        {COMMON_SVG_INSTRUCTIONS}
    """

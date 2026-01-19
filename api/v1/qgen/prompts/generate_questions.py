"""
Prompt template for generating questions.
"""

from typing import List, Dict, Optional

from .common_instructions import COMMON_INSTRUCTIONS

def generate_questions_prompt(
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

    Args:
        concepts: List of concept names to generate questions for
        concepts_descriptions: Mapping of concept name to description
        old_questions_on_concepts: Historical questions for reference
        n: Number of questions to generate
        question_type: Type of question (mcq4, short_answer, etc.)
        difficulty: Difficulty level (easy, medium, hard)
        instructions: Optional custom instructions from user

    Returns:
        Formatted prompt string for Gemini
    """
    # Build concept information
    concept_info = []
    for concept in concepts:
        desc = concepts_descriptions.get(concept, "No description available")
        concept_info.append(f"{concept}: {desc}")

    concepts_text = "\n".join(concept_info)

    instructions_block = (
        f"\nAdditional user instructions (prioritize these over anything concepts selected or difficulty or marks or anything): {instructions}"
        if instructions
        else ""
    )

    # Using f-string to avoid issues with curly braces in LaTeX examples
    return f"""
    You have access to these concepts and their descriptions:
    {concepts_text}
    
    Historical questions for reference: {old_questions_on_concepts}
    
    Generate {n} questions of type {question_type} with difficulty level: {difficulty}
    
    Instructions:
    - Choose concepts from the provided list above that are most relevant for each question
    - The questions should align with the specified difficulty level: {difficulty}
    - Use patterns from historical questions as reference but create original questions
    - Be strictly within the knowledge of the provided concepts, no external knowledge
    - Strictly use LaTeX format for mathematical entities like symbols and formulas
    - Strictly output all required fields for the question schema. Answer Text is mandatory, use LaTeX where needed
    - Question should  be Strictly Accurate and High Quality

    Common Latex Errors are:
        {COMMON_INSTRUCTIONS}
    {instructions_block}
    """

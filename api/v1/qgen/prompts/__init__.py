"""
Prompt templates for question generation endpoints.

This module contains all the base prompt functions used by the qgen API endpoints.
"""

from .auto_correct import auto_correct_questions_prompt
from .generate_questions import generate_questions_with_concepts_prompt
from .regenerate import regenerate_question_prompt
from .regenerate_with_prompt import regenerate_question_with_prompt_prompt

__all__ = [
    "auto_correct_questions_prompt",
    "generate_questions_with_concepts_prompt",
    "regenerate_question_prompt",
    "regenerate_question_with_prompt_prompt",
]

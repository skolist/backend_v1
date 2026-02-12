"""
Test data factories for creating consistent test objects.

These factories provide realistic test data that matches
the Supabase schema and API request/response structures.
"""

import uuid
from typing import Any, Dict, List, Optional


def create_test_concept(
    concept_id: Optional[str] = None,
    name: str = "Test Concept",
    description: str = "A test concept for unit testing.",
    topic_id: Optional[str] = None,
    page_number: int = 1,
) -> Dict[str, Any]:
    """Create a concept dict matching Supabase schema."""
    return {
        "id": concept_id or str(uuid.uuid4()),
        "name": name,
        "description": description,
        "topic_id": topic_id or str(uuid.uuid4()),
        "page_number": page_number,
    }


def create_test_activity(
    activity_id: Optional[str] = None,
    user_id: Optional[str] = None,
    name: str = "Test Activity",
    product_type: str = "QGEN",
) -> Dict[str, Any]:
    """Create an activity dict matching Supabase schema."""
    return {
        "id": activity_id or str(uuid.uuid4()),
        "name": name,
        "product_type": product_type,
        "user_id": user_id or str(uuid.uuid4()),
    }


def create_test_bank_question(
    question_id: Optional[str] = None,
    subject_id: Optional[str] = None,
    question_text: str = "What is Newton's First Law of Motion?",
    question_type: str = "mcq4",
    hardness_level: str = "easy",
) -> Dict[str, Any]:
    """Create a bank question dict matching Supabase schema."""
    base = {
        "id": question_id or str(uuid.uuid4()),
        "question_text": question_text,
        "question_type": question_type,
        "hardness_level": hardness_level,
        "marks": 1,
        "subject_id": subject_id or str(uuid.uuid4()),
    }
    
    if question_type == "mcq4":
        base.update({
            "option1": "Law of Inertia",
            "option2": "Law of Acceleration",
            "option3": "Law of Action-Reaction",
            "option4": "Law of Gravity",
            "correct_mcq_option": 1,
            "answer_text": "Law of Inertia",
            "explanation": "Newton's First Law states that an object at rest stays at rest.",
        })
    elif question_type == "short_answer":
        base.update({
            "answer_text": "An object at rest stays at rest unless acted upon by a force.",
            "explanation": "This is the law of inertia.",
        })
    elif question_type == "true_false":
        base.update({
            "correct_answer": True,
            "answer_text": "True",
            "explanation": "This statement is correct.",
        })
    elif question_type == "fill_in_the_blank":
        base.update({
            "answer_text": "inertia",
            "explanation": "The blank should be filled with 'inertia'.",
        })
    
    return base


def create_generate_questions_request(
    activity_id: Optional[str] = None,
    concept_ids: Optional[List[str]] = None,
    question_types: Optional[List[Dict[str, Any]]] = None,
    difficulty_distribution: Optional[Dict[str, int]] = None,
) -> Dict[str, Any]:
    """Create a generate_questions API request payload."""
    return {
        "activity_id": activity_id or str(uuid.uuid4()),
        "concept_ids": concept_ids or [str(uuid.uuid4())],
        "config": {
            "question_types": question_types or [{"type": "mcq4", "count": 2}],
            "difficulty_distribution": difficulty_distribution or {
                "easy": 50,
                "medium": 30,
                "hard": 20,
            },
        },
    }


def create_auto_correct_request(
    question_id: Optional[str] = None,
    question_type: str = "mcq4",
    question_text: str = "What is the formula for kinetic energy?",
) -> Dict[str, Any]:
    """Create an auto_correct_question API request payload."""
    base = {
        "question_id": question_id or str(uuid.uuid4()),
        "question_type": question_type,
        "question_text": question_text,
    }
    
    if question_type == "mcq4":
        base.update({
            "option1": "KE = m*v",
            "option2": "KE = 1/2*m*v^2",
            "option3": "KE = m*g*h",
            "option4": "KE = m*v^2",
            "correct_mcq_option": 2,
        })
    elif question_type == "short_answer":
        base.update({
            "answer_text": "The kinetic energy formula is KE = 1/2 * m * v^2",
        })
    
    return base


def create_regenerate_request(
    question_id: Optional[str] = None,
    regeneration_type: str = "harder",
) -> Dict[str, Any]:
    """Create a regenerate_question API request payload."""
    return {
        "question_id": question_id or str(uuid.uuid4()),
        "regeneration_type": regeneration_type,
    }


def create_regenerate_with_prompt_request(
    question_id: Optional[str] = None,
    prompt: str = "Make this question more challenging",
) -> Dict[str, Any]:
    """Create a regenerate_question_with_prompt API request payload."""
    return {
        "question_id": question_id or str(uuid.uuid4()),
        "prompt": prompt,
    }

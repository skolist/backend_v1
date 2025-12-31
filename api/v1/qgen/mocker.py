"""
Demo Question Functions
"""

import logging

from ai.schemas.questions import (
    MCQ4,
    MSQ4,
    FillInTheBlank,
    TrueFalse,
    ShortAnswer,
    LongAnswer,
)

logger = logging.getLogger(__name__)


def generate_mcq():
    """Dummy Function"""
    return MCQ4(
        question="What is the capital of France?",
        option1="Paris",
        option2="London",
        option3="Berlin",
        option4="Madrid",
        answer=1,
        explanation="Paris is the capital of France.",
    )


def generate_msq():
    """Dummy Function"""
    return MSQ4(
        question="What is the capital of France?",
        option1="Paris",
        option2="London",
        option3="Berlin",
        option4="Madrid",
        answers=[1, 2],
        explanation="Paris is the capital of France.",
    )


def generate_fill_in_the_blank():
    """Dummy Function"""
    return FillInTheBlank(
        question="What is the capital of France?",
        answer="Paris",
        explanation="Paris is the capital of France.",
    )


def generate_true_false():
    """Dummy Function"""
    return TrueFalse(
        question="What is the capital of France?",
        answer=True,
        explanation="Paris is the capital of France.",
    )


def generate_short_answer():
    """Dummy Function"""
    return ShortAnswer(
        question="What is the capital of France?",
        answer="Paris",
        explanation="Paris is the capital of France.",
    )


def generate_long_answer():
    """Dummy Function"""
    return LongAnswer(
        question="What is the capital of France?",
        answer="Paris",
        explanation="Paris is the capital of France.",
    )

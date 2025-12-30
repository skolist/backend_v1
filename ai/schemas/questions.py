"""
Schemas for various types of questions, to be generated using LLMs.
"""

from pydantic import BaseModel, Field


class MCQ4(BaseModel):
    """
    A schema representing a multiple-choice question with four options.
    """

    question: str = Field(
        ...,
        description=(
            "The question text, must not be empty. "
            "To be written using proper grammar and punctuation. "
            "Mathematical expressions should be formatted in LaTeX."
        ),
    )
    option1: str = Field(
        ...,
        description=(
            "The first answer option, must not be empty. "
            "To be written using proper grammar and punctuation. "
            "Mathematical expressions should be formatted in LaTeX.",
        ),
    )
    option2: str = Field(
        ...,
        description=(
            "The second answer option, must not be empty. "
            "To be written using proper grammar and punctuation. "
            "Mathematical expressions should be formatted in LaTeX."
        ),
    )
    option3: str = Field(
        ...,
        description=(
            "The third answer option, must not be empty. "
            "To be written using proper grammar and punctuation. "
            "Mathematical expressions should be formatted in LaTeX."
        ),
    )
    option4: str = Field(
        ...,
        description=(
            "The fourth answer option, must not be empty. "
            "To be written using proper grammar and punctuation. "
            "Mathematical expressions should be formatted in LaTeX."
        ),
    )
    answer: int = Field(
        ..., description="The index of the correct answer option (1-4)."
    )
    explanation: str = Field(
        ...,
        description=(
            "A detailed explanation of the correct answer, must not be empty. "
            "To be written using proper grammar and punctuation. "
            "Mathematical expressions should be formatted in LaTeX."
        ),
    )


class MSQ4(BaseModel):
    """
    A schema representing a multiple-select question with four options.
    """

    question: str = Field(
        ...,
        description=(
            "The question text, must not be empty. "
            "To be written using proper grammar and punctuation. "
            "Mathematical expressions should be formatted in LaTeX."
        ),
    )
    option1: str = Field(
        ...,
        description=(
            "The first answer option, must not be empty. "
            "To be written using proper grammar and punctuation. "
            "Mathematical expressions should be formatted in LaTeX."
        ),
    )
    option2: str = Field(
        ...,
        description=(
            "The second answer option, must not be empty. "
            "To be written using proper grammar and punctuation. "
            "Mathematical expressions should be formatted in LaTeX."
        ),
    )
    option3: str = Field(
        ...,
        description=(
            "The third answer option, must not be empty. "
            "To be written using proper grammar and punctuation. "
            "Mathematical expressions should be formatted in LaTeX."
        ),
    )
    option4: str = Field(
        ...,
        description=(
            "The fourth answer option, must not be empty. "
            "To be written using proper grammar and punctuation. "
            "Mathematical expressions should be formatted in LaTeX."
        ),
    )
    answers: list[int] = Field(
        ..., description="A list of indices of the correct answer options (1-4)."
    )
    explanation: str = Field(
        ...,
        description=(
            "A detailed explanation of the correct answers, must not be empty. "
            "To be written using proper grammar and punctuation. "
            "Mathematical expressions should be formatted in LaTeX."
        ),
    )


class FillInTheBlank(BaseModel):
    """
    A schema representing a fill-in-the-blank question.
    """

    question: str = Field(
        ...,
        description=(
            "The question text with blanks indicated by underscores, must not be empty. "
            "To be written using proper grammar and punctuation. "
            "Mathematical expressions should be formatted in LaTeX."
        ),
    )
    answer: str = Field(
        ...,
        description=(
            "The correct answer to fill in the blank, must not be empty. "
            "To be written using proper grammar and punctuation. "
            "Mathematical expressions should be formatted in LaTeX."
        ),
    )
    explanation: str = Field(
        ...,
        description=(
            "A detailed explanation of the correct answer, must not be empty. "
            "To be written using proper grammar and punctuation. "
            "Mathematical expressions should be formatted in LaTeX."
        ),
    )


class TrueFalse(BaseModel):
    """
    A schema representing a true/false question.
    """

    question: str = Field(
        ...,
        description=(
            "The statement to be evaluated as true or false, must not be empty. "
            "To be written using proper grammar and punctuation. "
            "Mathematical expressions should be formatted in LaTeX."
        ),
    )
    answer: bool = Field(
        ...,
        description="The correct answer indicating whether the statement is true or false.",
    )
    explanation: str = Field(
        ...,
        description=(
            "A detailed explanation of the correct answer, must not be empty. "
            "To be written using proper grammar and punctuation. "
            "Mathematical expressions should be formatted in LaTeX."
        ),
    )


class ShortAnswer(BaseModel):
    """
    A schema representing a short answer question.
    """

    question: str = Field(
        ...,
        description=(
            "The question text, must not be empty. "
            "To be written using proper grammar and punctuation. "
            "Mathematical expressions should be formatted in LaTeX."
        ),
    )
    answer: str = Field(
        ...,
        description=(
            "The correct short answer, must not be empty. "
            "To be written using proper grammar and punctuation. "
            "Mathematical expressions should be formatted in LaTeX."
        ),
    )
    explanation: str = Field(
        ...,
        description=(
            "A detailed explanation of the correct answer, must not be empty. "
            "To be written using proper grammar and punctuation. "
            "Mathematical expressions should be formatted in LaTeX."
        ),
    )


class LongAnswer(BaseModel):
    """
    A schema representing a long answer question.
    """

    question: str = Field(
        ...,
        description=(
            "The question text, must not be empty. "
            "To be written using proper grammar and punctuation. "
            "Mathematical expressions should be formatted in LaTeX."
        ),
    )
    answer: str = Field(
        ...,
        description=(
            "The correct long answer, must not be empty. "
            "To be written using proper grammar and punctuation. "
            "Mathematical expressions should be formatted in LaTeX."
        ),
    )
    explanation: str = Field(
        ...,
        description=(
            "A detailed explanation of the correct answer, must not be empty. "
            "To be written using proper grammar and punctuation. "
            "Mathematical expressions should be formatted in LaTeX."
        ),
    )
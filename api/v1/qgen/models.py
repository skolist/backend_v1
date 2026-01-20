"""
Defines the Pydantic models relavant to qgen
"""

from typing import Union, Optional, Dict, List, Type

from pydantic import BaseModel, Field

from supabase_dir import PublicQuestionTypeEnumEnum


class MCQ4(BaseModel):
    """MCQ4 question schema for Gemini structured output."""

    question_text: Optional[str] = Field(default=None, description="The question text")
    option1: Optional[str] = Field(default=None, description="First option")
    option2: Optional[str] = Field(default=None, description="Second option")
    option3: Optional[str] = Field(default=None, description="Third option")
    option4: Optional[str] = Field(default=None, description="Fourth option")
    correct_mcq_option: Optional[int] = Field(
        default=None, description="Correct option (1-4)"
    )
    explanation: Optional[str] = Field(
        default=None, description="Explanation for the answer"
    )
    hardness_level: Optional[str] = Field(
        default=None, description="Difficulty: easy, medium, hard"
    )
    marks: Optional[int] = Field(default=None, description="Marks for this question")
    answer_text: Optional[str] = Field(
        default=None, description="Answer text if applicable"
    )


class MCQ4List(BaseModel):
    """List of MCQ4 questions."""

    questions: List[MCQ4]


class MSQ4(BaseModel):
    """MSQ4 question schema for Gemini structured output."""

    question_text: Optional[str] = Field(default=None, description="The question text")
    option1: Optional[str] = Field(default=None, description="First option")
    option2: Optional[str] = Field(default=None, description="Second option")
    option3: Optional[str] = Field(default=None, description="Third option")
    option4: Optional[str] = Field(default=None, description="Fourth option")
    msq_option1_answer: Optional[bool] = Field(
        default=None, description="Is option 1 correct"
    )
    msq_option2_answer: Optional[bool] = Field(
        default=None, description="Is option 2 correct"
    )
    msq_option3_answer: Optional[bool] = Field(
        default=None, description="Is option 3 correct"
    )
    msq_option4_answer: Optional[bool] = Field(
        default=None, description="Is option 4 correct"
    )
    explanation: Optional[str] = Field(
        default=None, description="Explanation for the answer"
    )
    hardness_level: Optional[str] = Field(
        default=None, description="Difficulty: easy, medium, hard"
    )
    marks: Optional[int] = Field(default=None, description="Marks for this question")
    answer_text: Optional[str] = Field(
        default=None, description="Answer text if applicable"
    )


class MSQ4List(BaseModel):
    """List of MSQ4 questions."""

    questions: List[MSQ4]


class FillInTheBlank(BaseModel):
    """Fill in the blank question schema for Gemini structured output."""

    question_text: Optional[str] = Field(
        default=None, description="The question text with blank"
    )
    answer_text: Optional[str] = Field(default=None, description="The correct answer")
    explanation: Optional[str] = Field(
        default=None, description="Explanation for the answer"
    )
    hardness_level: Optional[str] = Field(
        default=None, description="Difficulty: easy, medium, hard"
    )
    marks: Optional[int] = Field(default=None, description="Marks for this question")


class FillInTheBlankList(BaseModel):
    """List of FillInTheBlank questions."""

    questions: List[FillInTheBlank]


class TrueFalse(BaseModel):
    """True/False question schema for Gemini structured output."""

    question_text: Optional[str] = Field(
        default=None, description="The statement to evaluate"
    )
    answer_text: Optional[str] = Field(default=None, description="True or False")
    explanation: Optional[str] = Field(
        default=None, description="Explanation for the answer"
    )
    hardness_level: Optional[str] = Field(
        default=None, description="Difficulty: easy, medium, hard"
    )
    marks: Optional[int] = Field(default=None, description="Marks for this question")


class TrueFalseList(BaseModel):
    """List of TrueFalse questions."""

    questions: List[TrueFalse]


class ShortAnswer(BaseModel):
    """Short answer question schema for Gemini structured output."""

    question_text: Optional[str] = Field(default=None, description="The question text")
    answer_text: Optional[str] = Field(default=None, description="The short answer")
    explanation: Optional[str] = Field(
        default=None, description="Explanation for the answer"
    )
    hardness_level: Optional[str] = Field(
        default=None, description="Difficulty: easy, medium, hard"
    )
    marks: Optional[int] = Field(default=None, description="Marks for this question")


class ShortAnswerList(BaseModel):
    """List of ShortAnswer questions."""

    questions: List[ShortAnswer]


class LongAnswer(BaseModel):
    """Long answer question schema for Gemini structured output."""

    question_text: Optional[str] = Field(default=None, description="The question text")
    answer_text: Optional[str] = Field(default=None, description="The long answer")
    explanation: Optional[str] = Field(
        default=None, description="Explanation for the answer"
    )
    hardness_level: Optional[str] = Field(
        default=None, description="Difficulty: easy, medium, hard"
    )
    marks: Optional[int] = Field(default=None, description="Marks for this question")


class LongAnswerList(BaseModel):
    """List of LongAnswer questions."""

    questions: List[LongAnswer]


# Type alias for any question type
AllQuestions = Union[MCQ4, MSQ4, FillInTheBlank, TrueFalse, ShortAnswer, LongAnswer]


# Mapping from question type key to GenAI schema (list wrapper)
QUESTION_TYPE_TO_SCHEMA: Dict[str, Type[BaseModel]] = {
    "mcq4": MCQ4List,
    "msq4": MSQ4List,
    "fill_in_the_blank": FillInTheBlankList,
    "true_false": TrueFalseList,
    "short_answer": ShortAnswerList,
    "long_answer": LongAnswerList,
}

# Mapping from question type key to database enum value
QUESTION_TYPE_TO_ENUM: Dict[str, PublicQuestionTypeEnumEnum] = {
    "mcq4": PublicQuestionTypeEnumEnum.MCQ4,
    "msq4": PublicQuestionTypeEnumEnum.MSQ4,
    "fill_in_the_blank": PublicQuestionTypeEnumEnum.FILL_IN_THE_BLANKS,
    "true_false": PublicQuestionTypeEnumEnum.TRUE_OR_FALSE,
    "short_answer": PublicQuestionTypeEnumEnum.SHORT_ANSWER,
    "long_answer": PublicQuestionTypeEnumEnum.LONG_ANSWER,
}

QUESTION_TYPE_TO_FIELD = {
    "mcq4": "total_mcq4s",
    "msq4": "total_msq4s",
    "fill_in_the_blank": "total_fill_in_the_blanks",
    "true_false": "total_true_falses",
    "short_answer": "total_short_answers",
    "long_answer": "total_long_answers",
}


# Feedback models
class FeedbackItem(BaseModel):
    """Individual feedback item."""

    message: str = Field(..., description="Feedback message")
    priority: int = Field(..., description="Priority level (1-10)")


class FeedbackList(BaseModel):
    """List of feedback items."""

    feedbacks: List[FeedbackItem] = Field(
        ..., description="List of feedback items with message and priority"
    )

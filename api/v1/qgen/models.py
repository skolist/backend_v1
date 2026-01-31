"""
Defines the Pydantic models relavant to qgen
"""

from typing import Union, Optional, Dict, List, Type

from pydantic import BaseModel, Field

from supabase_dir import PublicQuestionTypeEnumEnum

class SVG(BaseModel):
    svg: str = Field(description="SVG relavant to the question if needed")

class MCQ4(BaseModel):
    """MCQ4 question schema for Gemini structured output."""

    question_text: str = Field(description="The question text")
    option1: str = Field(description="First option")
    option2: str = Field(description="Second option")
    option3: str = Field(description="Third option")
    option4: str = Field(description="Fourth option")
    correct_mcq_option: int = Field(
        description="Correct option (1-4)"
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
    svgs: Optional[List[SVG]] = Field(
        default=None, description="List of SVGs relavant to the question if needed"
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
    svgs: Optional[List[SVG]] = Field(
        default=None, description="List of SVGs relavant to the question if needed"
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
    svgs: Optional[List[SVG]] = Field(
        default=None, description="List of SVGs relavant to the question if needed"
    )


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
    svgs: Optional[List[SVG]] = Field(
        default=None, description="List of SVGs relavant to the question if needed"
    )

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
    svgs: Optional[List[SVG]] = Field(
        default=None, description="List of SVGs relavant to the question if needed"
    )


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
    svgs: Optional[List[SVG]] = Field(
        default=None, description="List of SVGs relavant to the question if needed"
    )


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


class AutoCorrectedQuestion(BaseModel):
    """Wrapper for auto-corrected question from Gemini."""

    question: AllQuestions = Field(..., description="The auto-corrected question")


class ExtractedQuestion(BaseModel):
    """Single extracted question with type discriminator for mixed-type extraction."""

    question_type: str = Field(
        description="Question type: mcq4, msq4, fill_in_the_blank, true_false, short_answer, long_answer"
    )
    question_text: str = Field(description="The question text")
    # MCQ4/MSQ4 options
    option1: Optional[str] = Field(default=None, description="First option (for MCQ/MSQ)")
    option2: Optional[str] = Field(default=None, description="Second option (for MCQ/MSQ)")
    option3: Optional[str] = Field(default=None, description="Third option (for MCQ/MSQ)")
    option4: Optional[str] = Field(default=None, description="Fourth option (for MCQ/MSQ)")
    # MCQ4 answer
    correct_mcq_option: Optional[int] = Field(
        default=None, description="Correct option (1-4) for MCQ4"
    )
    # MSQ4 answers
    msq_option1_answer: Optional[bool] = Field(
        default=None, description="Is option 1 correct (for MSQ4)"
    )
    msq_option2_answer: Optional[bool] = Field(
        default=None, description="Is option 2 correct (for MSQ4)"
    )
    msq_option3_answer: Optional[bool] = Field(
        default=None, description="Is option 3 correct (for MSQ4)"
    )
    msq_option4_answer: Optional[bool] = Field(
        default=None, description="Is option 4 correct (for MSQ4)"
    )
    # Common fields
    answer_text: Optional[str] = Field(
        default=None, description="Answer text (for fill_in_blank, true_false, short_answer, long_answer)"
    )
    explanation: Optional[str] = Field(default=None, description="Explanation for the answer")
    hardness_level: Optional[str] = Field(
        default=None, description="Difficulty: easy, medium, hard"
    )
    marks: Optional[int] = Field(default=None, description="Marks for this question")
    svgs: Optional[List[SVG]] = Field(
        default=None, description="List of SVGs relevant to the question if needed"
    )


class ExtractedQuestionsList(BaseModel):
    """List of extracted questions of various types."""

    questions: List[ExtractedQuestion] = Field(
        description="List of extracted questions from the file"
    )

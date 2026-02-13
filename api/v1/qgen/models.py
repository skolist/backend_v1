"""
Defines the Pydantic models relavant to qgen
"""

from pydantic import BaseModel, Field

from supabase_dir import PublicQuestionTypeEnumEnum


class SVG(BaseModel):
    svg: str = Field(description="SVG relavant to the question if needed")


class Column(BaseModel):
    name: str = Field(description="Column header, e.g., 'Column A' or 'List I'")
    items: list[str] = Field(description="Items in the column")


class MCQ4(BaseModel):
    """MCQ4 question schema for Gemini structured output."""

    question_text: str = Field(description="The question text")
    option1: str = Field(description="First option")
    option2: str = Field(description="Second option")
    option3: str = Field(description="Third option")
    option4: str = Field(description="Fourth option")
    correct_mcq_option: int = Field(description="Correct option (1-4)")
    explanation: str | None = Field(default=None, description="Explanation for the answer")
    hardness_level: str | None = Field(default=None, description="Difficulty: easy, medium, hard")
    marks: int | None = Field(default=None, description="Marks for this question")
    answer_text: str | None = Field(default=None, description="Answer text if applicable")
    svgs: list[SVG] | None = Field(default=None, description="List of SVGs relavant to the question if needed")


class MCQ4List(BaseModel):
    """List of MCQ4 questions."""

    questions: list[MCQ4]


class MSQ4(BaseModel):
    """MSQ4 question schema for Gemini structured output."""

    question_text: str | None = Field(default=None, description="The question text")
    option1: str | None = Field(default=None, description="First option")
    option2: str | None = Field(default=None, description="Second option")
    option3: str | None = Field(default=None, description="Third option")
    option4: str | None = Field(default=None, description="Fourth option")
    msq_option1_answer: bool | None = Field(default=None, description="Is option 1 correct")
    msq_option2_answer: bool | None = Field(default=None, description="Is option 2 correct")
    msq_option3_answer: bool | None = Field(default=None, description="Is option 3 correct")
    msq_option4_answer: bool | None = Field(default=None, description="Is option 4 correct")
    explanation: str | None = Field(default=None, description="Explanation for the answer")
    hardness_level: str | None = Field(default=None, description="Difficulty: easy, medium, hard")
    marks: int | None = Field(default=None, description="Marks for this question")
    answer_text: str | None = Field(default=None, description="Answer text if applicable")
    svgs: list[SVG] | None = Field(default=None, description="List of SVGs relavant to the question if needed")


class MSQ4List(BaseModel):
    """List of MSQ4 questions."""

    questions: list[MSQ4]


class FillInTheBlank(BaseModel):
    """Fill in the blank question schema for Gemini structured output."""

    question_text: str | None = Field(default=None, description="The question text with blank")
    answer_text: str | None = Field(default=None, description="The correct answer")
    explanation: str | None = Field(default=None, description="Explanation for the answer")
    hardness_level: str | None = Field(default=None, description="Difficulty: easy, medium, hard")
    marks: int | None = Field(default=None, description="Marks for this question")
    svgs: list[SVG] | None = Field(default=None, description="List of SVGs relavant to the question if needed")


class FillInTheBlankList(BaseModel):
    """List of FillInTheBlank questions."""

    questions: list[FillInTheBlank]


class TrueFalse(BaseModel):
    """True/False question schema for Gemini structured output."""

    question_text: str | None = Field(default=None, description="The statement to evaluate")
    answer_text: str | None = Field(default=None, description="True or False")
    explanation: str | None = Field(default=None, description="Explanation for the answer")
    hardness_level: str | None = Field(default=None, description="Difficulty: easy, medium, hard")
    marks: int | None = Field(default=None, description="Marks for this question")
    svgs: list[SVG] | None = Field(default=None, description="List of SVGs relavant to the question if needed")


class TrueFalseList(BaseModel):
    """List of TrueFalse questions."""

    questions: list[TrueFalse]


class ShortAnswer(BaseModel):
    """Short answer question schema for Gemini structured output."""

    question_text: str | None = Field(default=None, description="The question text")
    answer_text: str | None = Field(default=None, description="The short answer")
    explanation: str | None = Field(default=None, description="Explanation for the answer")
    hardness_level: str | None = Field(default=None, description="Difficulty: easy, medium, hard")
    marks: int | None = Field(default=None, description="Marks for this question")
    svgs: list[SVG] | None = Field(default=None, description="List of SVGs relavant to the question if needed")


class ShortAnswerList(BaseModel):
    """List of ShortAnswer questions."""

    questions: list[ShortAnswer]


class LongAnswer(BaseModel):
    """Long answer question schema for Gemini structured output."""

    question_text: str | None = Field(default=None, description="The question text")
    answer_text: str | None = Field(default=None, description="The long answer")
    explanation: str | None = Field(default=None, description="Explanation for the answer")
    hardness_level: str | None = Field(default=None, description="Difficulty: easy, medium, hard")
    marks: int | None = Field(default=None, description="Marks for this question")
    svgs: list[SVG] | None = Field(default=None, description="List of SVGs relavant to the question if needed")


class LongAnswerList(BaseModel):
    """List of LongAnswer questions."""

    questions: list[LongAnswer]


class MatchTheFollowing(BaseModel):
    "Match the following question schema for Gemini structured output."

    question_text: str | None = Field(
        default=None, description="The main question text, like Match The Following Things"
    )
    columns: list[Column] = Field(default=None, description="List of columns for matching")
    answer_text: str | None = Field(default=None, description="The answer text")
    explanation: str | None = Field(default=None, description="Explanation for the answer")
    hardness_level: str | None = Field(default=None, description="Difficulty: easy, medium, hard")
    marks: int | None = Field(default=None, description="Marks for this question")
    svgs: list[SVG] | None = Field(default=None, description="List of SVGs relavant to the question if needed")


class MatchTheFollowingList(BaseModel):
    """List of MatchTheFollowing questions."""

    questions: list[MatchTheFollowing]


# Type alias for any question type
AllQuestions = MCQ4 | MSQ4 | FillInTheBlank | TrueFalse | ShortAnswer | LongAnswer | MatchTheFollowing


# Mapping from question type key to GenAI schema (list wrapper)
QUESTION_TYPE_TO_SCHEMA: dict[str, type[BaseModel]] = {
    "mcq4": MCQ4List,
    "msq4": MSQ4List,
    "fill_in_the_blank": FillInTheBlankList,
    "true_false": TrueFalseList,
    "short_answer": ShortAnswerList,
    "long_answer": LongAnswerList,
    "match_the_following": MatchTheFollowingList,
}

# Mapping from question type key to database enum value
QUESTION_TYPE_TO_ENUM: dict[str, PublicQuestionTypeEnumEnum] = {
    "mcq4": PublicQuestionTypeEnumEnum.MCQ4,
    "msq4": PublicQuestionTypeEnumEnum.MSQ4,
    "fill_in_the_blank": PublicQuestionTypeEnumEnum.FILL_IN_THE_BLANKS,
    "true_false": PublicQuestionTypeEnumEnum.TRUE_OR_FALSE,
    "short_answer": PublicQuestionTypeEnumEnum.SHORT_ANSWER,
    "long_answer": PublicQuestionTypeEnumEnum.LONG_ANSWER,
    "match_the_following": PublicQuestionTypeEnumEnum.MATCH_THE_FOLLOWING,
}

QUESTION_TYPE_TO_FIELD = {
    "mcq4": "total_mcq4s",
    "msq4": "total_msq4s",
    "fill_in_the_blank": "total_fill_in_the_blanks",
    "true_false": "total_true_falses",
    "short_answer": "total_short_answers",
    "long_answer": "total_long_answers",
    "match_the_following": "match_the_following_count",
}


# Feedback models
class FeedbackItem(BaseModel):
    """Individual feedback item."""

    message: str = Field(..., description="Feedback message")
    priority: int = Field(..., description="Priority level (1-10)")


class FeedbackList(BaseModel):
    """List of feedback items."""

    feedbacks: list[FeedbackItem] = Field(..., description="List of feedback items with message and priority")


class AutoCorrectedQuestion(BaseModel):
    """Wrapper for auto-corrected question from Gemini."""

    question: AllQuestions = Field(..., description="The auto-corrected question")


class ExtractedQuestion(BaseModel):
    """Single extracted question with type discriminator for mixed-type extraction."""

    question_type: str = Field(
        description="Question type: mcq4, msq4, fill_in_the_blank, "
        "true_false, short_answer, long_answer, match_the_following"
    )
    question_text: str = Field(description="The question text")
    # MCQ4/MSQ4 options
    option1: str | None = Field(default=None, description="First option (for MCQ/MSQ)")
    option2: str | None = Field(default=None, description="Second option (for MCQ/MSQ)")
    option3: str | None = Field(default=None, description="Third option (for MCQ/MSQ)")
    option4: str | None = Field(default=None, description="Fourth option (for MCQ/MSQ)")
    # MCQ4 answer
    correct_mcq_option: int | None = Field(default=None, description="Correct option (1-4) for MCQ4")
    # MSQ4 answers
    msq_option1_answer: bool | None = Field(default=None, description="Is option 1 correct (for MSQ4)")
    msq_option2_answer: bool | None = Field(default=None, description="Is option 2 correct (for MSQ4)")
    msq_option3_answer: bool | None = Field(default=None, description="Is option 3 correct (for MSQ4)")
    msq_option4_answer: bool | None = Field(default=None, description="Is option 4 correct (for MSQ4)")
    # Match the following fields
    columns: list[Column] = Field(default=None, description="List of columns for matching")
    # Common fields
    answer_text: str | None = Field(
        default=None,
        description="Answer text (for fill_in_blank, true_false, short_answer, long_answer)",
    )
    explanation: str | None = Field(default=None, description="Explanation for the answer")
    hardness_level: str | None = Field(default=None, description="Difficulty: easy, medium, hard")
    marks: int | None = Field(default=None, description="Marks for this question")
    svgs: list[SVG] | None = Field(default=None, description="List of SVGs relevant to the question if needed")


class ExtractedQuestionsList(BaseModel):
    """List of extracted questions of various types."""

    questions: list[ExtractedQuestion] = Field(description="List of extracted questions from the file")

"""
New Pydantic models for question generation with granular concept association.
"""

from pydantic import BaseModel, Field

from ..models import (
    MCQ4,
    MSQ4,
    FillInTheBlank,
    LongAnswer,
    MatchTheFollowing,
    ShortAnswer,
    TrueFalse,
)


class MCQ4WithConcepts(MCQ4):
    concepts: list[str] = Field(..., description="List of concept names relevant to this specific question")


class MCQ4WithConceptsList(BaseModel):
    questions: list[MCQ4WithConcepts]


class MSQ4WithConcepts(MSQ4):
    concepts: list[str] = Field(..., description="List of concept names relevant to this specific question")


class MSQ4WithConceptsList(BaseModel):
    questions: list[MSQ4WithConcepts]


class FillInTheBlankWithConcepts(FillInTheBlank):
    concepts: list[str] = Field(..., description="List of concept names relevant to this specific question")


class FillInTheBlankWithConceptsList(BaseModel):
    questions: list[FillInTheBlankWithConcepts]


class TrueFalseWithConcepts(TrueFalse):
    concepts: list[str] = Field(..., description="List of concept names relevant to this specific question")


class TrueFalseWithConceptsList(BaseModel):
    questions: list[TrueFalseWithConcepts]


class ShortAnswerWithConcepts(ShortAnswer):
    concepts: list[str] = Field(..., description="List of concept names relevant to this specific question")


class ShortAnswerWithConceptsList(BaseModel):
    questions: list[ShortAnswerWithConcepts]


class LongAnswerWithConcepts(LongAnswer):
    concepts: list[str] = Field(..., description="List of concept names relevant to this specific question")


class LongAnswerWithConceptsList(BaseModel):
    questions: list[LongAnswerWithConcepts]


class MatchTheFollowingWithConcepts(MatchTheFollowing):
    concepts: list[str] = Field(..., description="List of concept names relevant to this specific question")


class MatchTheFollowingWithConceptsList(BaseModel):
    questions: list[MatchTheFollowingWithConcepts]


QUESTION_TYPE_TO_SCHEMA_WITH_CONCEPTS: dict[str, type[BaseModel]] = {
    "mcq4": MCQ4WithConceptsList,
    "msq4": MSQ4WithConceptsList,
    "fill_in_the_blank": FillInTheBlankWithConceptsList,
    "true_false": TrueFalseWithConceptsList,
    "short_answer": ShortAnswerWithConceptsList,
    "long_answer": LongAnswerWithConceptsList,
    "match_the_following": MatchTheFollowingWithConceptsList,
}

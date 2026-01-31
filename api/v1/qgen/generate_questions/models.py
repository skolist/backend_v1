"""
New Pydantic models for question generation with granular concept association.
"""

from typing import List, Type, Dict
from pydantic import Field, BaseModel
from ..models import (
    MCQ4, MSQ4, FillInTheBlank, TrueFalse, ShortAnswer, LongAnswer, MatchTheFollowing,
    QUESTION_TYPE_TO_ENUM
)

class MCQ4WithConcepts(MCQ4):
    concepts: List[str] = Field(..., description="List of concept names relevant to this specific question")

class MCQ4WithConceptsList(BaseModel):
    questions: List[MCQ4WithConcepts]

class MSQ4WithConcepts(MSQ4):
    concepts: List[str] = Field(..., description="List of concept names relevant to this specific question")

class MSQ4WithConceptsList(BaseModel):
    questions: List[MSQ4WithConcepts]

class FillInTheBlankWithConcepts(FillInTheBlank):
    concepts: List[str] = Field(..., description="List of concept names relevant to this specific question")

class FillInTheBlankWithConceptsList(BaseModel):
    questions: List[FillInTheBlankWithConcepts]

class TrueFalseWithConcepts(TrueFalse):
    concepts: List[str] = Field(..., description="List of concept names relevant to this specific question")

class TrueFalseWithConceptsList(BaseModel):
    questions: List[TrueFalseWithConcepts]

class ShortAnswerWithConcepts(ShortAnswer):
    concepts: List[str] = Field(..., description="List of concept names relevant to this specific question")

class ShortAnswerWithConceptsList(BaseModel):
    questions: List[ShortAnswerWithConcepts]

class LongAnswerWithConcepts(LongAnswer):
    concepts: List[str] = Field(..., description="List of concept names relevant to this specific question")

class LongAnswerWithConceptsList(BaseModel):
    questions: List[LongAnswerWithConcepts]

class MatchTheFollowingWithConcepts(MatchTheFollowing):
    concepts: List[str] = Field(..., description="List of concept names relevant to this specific question")

class MatchTheFollowingWithConceptsList(BaseModel):
    questions: List[MatchTheFollowingWithConcepts]

QUESTION_TYPE_TO_SCHEMA_WITH_CONCEPTS: Dict[str, Type[BaseModel]] = {
    "mcq4": MCQ4WithConceptsList,
    "msq4": MSQ4WithConceptsList,
    "fill_in_the_blank": FillInTheBlankWithConceptsList,
    "true_false": TrueFalseWithConceptsList,
    "short_answer": ShortAnswerWithConceptsList,
    "long_answer": LongAnswerWithConceptsList,
    "match_the_following": MatchTheFollowingWithConceptsList,
}

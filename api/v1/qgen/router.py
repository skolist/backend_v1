# pylint: disable=cell-var-from-loop
# pylint: disable=broad-exception-caught
# pylint: disable=too-many-locals
"""
Router for the dummy endpoint
"""
import os
import logging
import uuid
from typing import List, Literal

import google.genai as genai
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from supabase import Client

from ai.prompts.qgen import (
    generate_question_distribution_prompt,
    generate_questions_prompt,
)
from ai.schemas.qgen import ConceptQuestionTypeDistribution, TotalQuestionTypeCounts
from ai.schemas.questions import (
    MCQ4,
    MSQ4,
    FillInTheBlank,
    TrueFalse,
    ShortAnswer,
    LongAnswer,
    ALL_QUESTIONS,
)
from api.v1.auth import get_supabase_client
from api.v1.qgen import mocker

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/generate", tags=["generation"])


class QuestionTypeConfig(BaseModel):
    """
    Question Type Configuration
    """

    type: Literal[
        "mcq4", "short_answer", "long_answer", "true_false", "fill_in_the_blank", "msq4"
    ]
    count: int


class DifficultyDistribution(BaseModel):
    """
    Difficulty Distribution Configuration
    """

    easy: int = Field(..., ge=0, le=100)
    medium: int = Field(..., ge=0, le=100)
    hard: int = Field(..., ge=0, le=100)


class QuestionConfig(BaseModel):
    """
    Question Configuration
    """

    question_types: List[QuestionTypeConfig]
    difficulty_distribution: DifficultyDistribution


class GenerateQuestionsRequest(BaseModel):
    """
    Generate Questions Request
    """

    activity_id: uuid.UUID
    concept_ids: List[uuid.UUID]
    config: QuestionConfig


class GenerateQuestionsResponse(BaseModel):
    """
    Generate Questions Response
    """

    success: bool
    message: str
    data: dict


def extract_total_question_type_counts(
    request: GenerateQuestionsRequest,
) -> TotalQuestionTypeCounts:
    QUESTION_TYPE_TO_FIELD = {
        "mcq4": "total_mcq4s",
        "msq4": "total_msq4s",
        "fill_in_the_blank": "total_fill_in_the_blanks",
        "true_false": "total_true_falses",
        "short_answer": "total_short_answers",
        "long_answer": "total_long_answers",
    }

    totals = TotalQuestionTypeCounts()

    for qt in request.config.question_types:
        field_name = QUESTION_TYPE_TO_FIELD.get(qt.type)
        if not field_name:
            continue  # or raise if you want strictness

        setattr(
            totals,
            field_name,
            getattr(totals, field_name) + qt.count,
        )

    return totals


@router.post("/questions", response_model=GenerateQuestionsResponse)
def generate_questions(
    request: GenerateQuestionsRequest,
    supabase: Client = Depends(get_supabase_client),
):

    # Code to fetch the concepts from the ids
    concepts = (
        supabase.table("concepts")
        .select("name, description")
        .eq("id", request.concept_ids)
        .execute()
        .data
    )
    concepts_dict = {concept["name"]: concept["description"] for concept in concepts}
    # Code to fetch the old questions for this concepts from supabase
    old_questions = (
        supabase.table("bank_questions")
        .select("*")
        .eq("concept_id", request.concept_ids)
        .execute()
        .data
    )

    # Forming the question type count mapping using the request
    question_type_count_mapping = extract_total_question_type_counts(request)

    # Code to generate the concept to number of question type mapping
    gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    response = gemini_client.models.generate_content(
        model="gemini-2.0-flash-exp",
        contents=generate_question_distribution_prompt(
            question_type_count_dict=question_type_count_mapping.dict(),
            concepts_list=concepts,
            old_questions_on_this_concepts=old_questions,
        ),
        config={
            "response_mime_type": "application/json",
            "response_schema": ConceptQuestionTypeDistribution,
        },
    )
    distribution: ConceptQuestionTypeDistribution = response.parsed

    # Code to generate the questions
    all_questions: List[ALL_QUESTIONS] = []
    QUESTION_TYPE_TO_BASE_MODEL = {
        "mcq4": MCQ4,
        "msq4": MSQ4,
        "fill_in_the_blank": FillInTheBlank,
        "true_false": TrueFalse,
        "short_answer": ShortAnswer,
        "long_answer": LongAnswer,
    }
    # Need to iterate over the distribution and generate the questions per concept
    for concept_name, question_type_count in distribution.distribution.items():
        # Iterating over all types
        for question_type, count in question_type_count.items():
            # Code to generate the questions
            questions = gemini_client.models.generate_content(
                model="gemini-2.0-flash-exp",
                contents=generate_questions_prompt(
                    concept=concept_name,
                    description=concepts_dict.get(concept_name),
                    old_questions_on_this_concept=old_questions,
                    n=count,
                    question_type=question_type,
                ),
                config={
                    "response_mime_type": "application/json",
                    "response_schema": List[
                        QUESTION_TYPE_TO_BASE_MODEL.get(question_type)
                    ],
                },
            )
            all_questions.extend(questions.parsed)

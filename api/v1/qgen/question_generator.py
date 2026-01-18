"""
Consolidated Question Generator API
All question generation logic in one place - schemas, prompts, and endpoint.
"""

import os
import logging
import uuid
from typing import List, Literal, Dict

from google import genai
from fastapi import Depends, status
from fastapi.responses import Response
from pydantic import BaseModel, Field
import supabase

from api.v1.auth import get_supabase_client
from supabase_dir import (
    PublicHardnessLevelEnumEnum,
    GenQuestionsInsert,
    GenQuestionsConceptsMapsInsert,
)
from .models import (
    AllQuestions,
    QUESTION_TYPE_TO_SCHEMA,
    QUESTION_TYPE_TO_ENUM,
    QUESTION_TYPE_TO_FIELD,
)

logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION SCHEMAS
# ============================================================================


class TotalQuestionTypeCounts(BaseModel):
    """Total counts for each question type across all concepts."""

    total_mcq4s: int = 0
    total_msq4s: int = 0
    total_fill_in_the_blanks: int = 0
    total_true_falses: int = 0
    total_short_answers: int = 0
    total_long_answers: int = 0


class QuestionTypeDistribution(BaseModel):
    """Distribution of question types for a single concept."""

    mcq4: int = Field(
        default=0, description="The number of MCQ4 questions to be generated."
    )
    msq4: int = Field(
        default=0, description="The number of MSQ4 questions to be generated."
    )
    fill_in_the_blank: int = Field(
        default=0,
        description="The number of Fill-in-the-Blank questions to be generated.",
    )
    true_false: int = Field(
        default=0, description="The number of True/False questions to be generated."
    )
    short_answer: int = Field(
        default=0, description="The number of Short Answer questions to be generated."
    )
    long_answer: int = Field(
        default=0, description="The number of Long Answer questions to be generated."
    )


class ConceptDistributionItem(BaseModel):
    """Distribution of question types for a single concept (with concept name)."""

    concept_name: str = Field(..., description="The name of the concept")
    question_counts: QuestionTypeDistribution = Field(
        ..., description="The counts of each question type for this concept"
    )


class ConceptQuestionTypeDistribution(BaseModel):
    """Distribution of question types across multiple concepts."""

    distribution: List[ConceptDistributionItem] = Field(
        ...,
        description="List of concept distributions with question type counts for each concept.",
    )


class QuestionTypeConfig(BaseModel):
    """Question Type Configuration for the request."""

    type: Literal[
        "mcq4", "short_answer", "long_answer", "true_false", "fill_in_the_blank", "msq4"
    ]
    count: int


class DifficultyDistribution(BaseModel):
    """Difficulty Distribution Configuration."""

    easy: int = Field(..., ge=0, le=100)
    medium: int = Field(..., ge=0, le=100)
    hard: int = Field(..., ge=0, le=100)


class QuestionConfig(BaseModel):
    """Question Configuration."""

    question_types: List[QuestionTypeConfig]
    difficulty_distribution: DifficultyDistribution


class GenerateQuestionsRequest(BaseModel):
    """Generate Questions Request."""

    activity_id: uuid.UUID
    concept_ids: List[uuid.UUID]
    config: QuestionConfig


# ============================================================================
# PROMPT FUNCTIONS
# ============================================================================


def generate_question_distribution_prompt(
    question_type_count_dict: TotalQuestionTypeCounts,
    concepts_list: List[str],
    old_questions_on_this_concepts: Dict[str, List[AllQuestions]],
) -> str:
    """Generate prompt for distributing questions across concepts."""

    prompt = """
    We have this list of concepts: {concepts_list}
    We have this list of old questions based on these concepts: {old_questions_on_this_concepts}
    We know how much of each type of questions should be there in our distribution: {question_type_count_dict}
    Now based on this historical data of old questions, and our current total requirements of each type of questions, generate a distribution of number of questions of certain type for each concept.
    You should output the name of the concept as it is in distribution without any changes.
    """

    return prompt.format(
        concepts_list=concepts_list,
        old_questions_on_this_concepts=old_questions_on_this_concepts,
        question_type_count_dict=question_type_count_dict,
    )


def generate_questions_prompt(
    concept: str,
    description: str,
    old_questions_on_this_concept: List[AllQuestions],
    n: int,
    question_type: str,
) -> str:
    """Generate prompt for creating questions for a specific concept."""

    prompt = """
    We have this concept and its description: {concept} : {description}
    We have this list of old questions based on this concept: {old_questions_on_this_concept}
    We want to generate {n} questions of type {question_type}
    The questions should be based on the concept and its description, and the old questions. Try to align with the patterns in the old questions.
    Be strictly within the knowledge of the concept and its description, no external knowledge is allowed.
    Strictly Use Latex format for Mathematical entities like symbols and formula etc.
    Strictly output all the fields required for the question in the format specified in the question schema. Answer Text is also compulsory , that too in latex wherever required
    """

    return prompt.format(
        concept=concept,
        description=description,
        old_questions_on_this_concept=old_questions_on_this_concept,
        n=n,
        question_type=question_type,
    )


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def extract_total_question_type_counts(
    request: GenerateQuestionsRequest,
) -> TotalQuestionTypeCounts:
    """Extract total question type counts from the request."""

    totals = TotalQuestionTypeCounts()

    for qt in request.config.question_types:
        field_name = QUESTION_TYPE_TO_FIELD.get(qt.type)
        if not field_name:
            continue

        setattr(
            totals,
            field_name,
            getattr(totals, field_name) + qt.count,
        )

    return totals


# ============================================================================
# CORE LOGIC FUNCTIONS (No Supabase dependency)
# ============================================================================


def generate_distribution(
    gemini_client: genai.Client,
    question_type_counts: TotalQuestionTypeCounts,
    concepts: List[Dict[str, str]],
    old_questions: List[dict],
) -> ConceptQuestionTypeDistribution:
    """
    Generate distribution of question types across concepts using GenAI.

    Args:
        gemini_client: Initialized Gemini client
        question_type_counts: Total counts for each question type
        concepts: List of concept dicts with 'name' and 'description'
        old_questions: List of historical questions for reference

    Returns:
        ConceptQuestionTypeDistribution with question counts per concept
    """
    response = gemini_client.models.generate_content(
        model="gemini-3-flash-preview",
        contents=generate_question_distribution_prompt(
            question_type_count_dict=question_type_counts.model_dump(),
            concepts_list=concepts,
            old_questions_on_this_concepts=old_questions,
        ),
        config={
            "response_mime_type": "application/json",
            "response_schema": ConceptQuestionTypeDistribution,
        },
    )
    return response.parsed


def generate_questions_for_distribution(
    gemini_client: genai.Client,
    distribution: ConceptQuestionTypeDistribution,
    concepts_dict: Dict[str, str],
    concepts_name_to_id: Dict[str, str],
    old_questions: List[dict],
    activity_id: uuid.UUID,
    default_hardness: PublicHardnessLevelEnumEnum = PublicHardnessLevelEnumEnum.MEDIUM,
    default_marks: int = 1,
) -> List[Dict[str, any]]:
    """
    Generate questions based on the distribution using GenAI.

    Args:
        gemini_client: Initialized Gemini client
        distribution: Distribution of question types across concepts
        concepts_dict: Mapping of concept name to description
        concepts_name_to_id: Mapping of concept name to concept ID
        old_questions: List of historical questions for reference
        activity_id: UUID of the activity these questions belong to
        default_hardness: Default hardness level for generated questions
        default_marks: Default marks for generated questions

    Returns:
        List of dicts with 'question' (GenQuestionsInsert-compatible) and 'concept_id'
    """
    gen_questions_data: List[Dict[str, any]] = []

    for concept_item in distribution.distribution:
        concept_name = concept_item.concept_name
        question_type_count = concept_item.question_counts

        concept_id = concepts_name_to_id.get(concept_name)
        if not concept_id:
            logger.warning(f"Concept ID not found for: {concept_name}")
            continue

        for question_type, count in question_type_count.model_dump().items():
            if count == 0:
                continue

            # Get the appropriate schema for this question type
            question_schema = QUESTION_TYPE_TO_SCHEMA.get(question_type)
            question_type_enum = QUESTION_TYPE_TO_ENUM.get(question_type)
            if not question_schema or not question_type_enum:
                logger.warning(f"Unknown question type: {question_type}")
                continue

            # Generate questions for this concept and type
            questions_response = gemini_client.models.generate_content(
                model="gemini-3-flash-preview",
                contents=generate_questions_prompt(
                    concept=concept_name,
                    description=concepts_dict.get(concept_name, ""),
                    old_questions_on_this_concept=old_questions,
                    n=count,
                    question_type=question_type,
                ),
                config={
                    "response_mime_type": "application/json",
                    "response_schema": question_schema,
                },
            )
            try:
                for q in questions_response.parsed.questions:
                    gen_question_dict = {
                        **q.model_dump(),
                        "activity_id": str(activity_id),
                        "question_type": question_type_enum,
                        "hardness_level": default_hardness,
                        "marks": default_marks,
                    }
                    gen_questions_data.append(
                        {
                            "question": gen_question_dict,
                            "concept_id": concept_id,
                        }
                    )
            except Exception as e:
                logger.error(f"Error parsing questions response: {e}", exc_info=True)

    return gen_questions_data


# ============================================================================
# API ENDPOINT (Wrapper with Supabase integration)
# ============================================================================


def generate_questions(
    request: GenerateQuestionsRequest,
    supabase_client: supabase.Client = Depends(get_supabase_client),
) -> Response:
    """
    Generate questions based on concepts and configuration.

    This endpoint orchestrates:
    1. Fetches concepts and historical questions from Supabase
    2. Calls generate_distribution() to get question distribution
    3. Calls generate_questions_for_distribution() to create questions
    4. Inserts generated questions into gen_questions table
    5. Creates concept-question mappings in gen_questions_concepts_maps table

    Returns:
        201 Created on success
        500 Internal Server Error on failure
    """
    try:
        # ====================================================================
        # DATA FETCHING (Supabase)
        # ====================================================================

        # Fetch concepts from the database
        concepts = (
            supabase_client.table("concepts")
            .select("id, name, description")
            .in_("id", [str(cid) for cid in request.concept_ids])
            .execute()
            .data
        )
        concepts_dict = {
            concept["name"]: concept["description"] for concept in concepts
        }
        concepts_name_to_id = {concept["name"]: concept["id"] for concept in concepts}

        # Fetch old questions for these concepts via the mapping table
        # First get the bank_question_ids from the mapping table
        concept_maps = (
            supabase_client.table("bank_questions_concepts_maps")
            .select("bank_question_id")
            .in_("concept_id", [str(cid) for cid in request.concept_ids])
            .execute()
            .data
        )
        bank_question_ids = list({m["bank_question_id"] for m in concept_maps})

        # Then fetch the bank questions
        if bank_question_ids:
            old_questions = (
                supabase_client.table("bank_questions")
                .select("*")
                .in_("id", bank_question_ids)
                .execute()
                .data
            )
        else:
            old_questions = []

        # ====================================================================
        # QUESTION GENERATION (Pure Logic)
        # ====================================================================

        # Extract total question type counts from request
        question_type_counts = extract_total_question_type_counts(request)

        # Initialize Gemini client
        gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

        # Step 1: Generate distribution
        distribution = generate_distribution(
            gemini_client=gemini_client,
            question_type_counts=question_type_counts,
            concepts=concepts,
            old_questions=old_questions,
        )

        # Step 2: Generate questions based on distribution
        gen_questions_data = generate_questions_for_distribution(
            gemini_client=gemini_client,
            distribution=distribution,
            concepts_dict=concepts_dict,
            concepts_name_to_id=concepts_name_to_id,
            old_questions=old_questions,
            activity_id=request.activity_id,
        )

        # ====================================================================
        # DATABASE INSERTION (Supabase)
        # ====================================================================

        for item in gen_questions_data:
            question_data = item["question"]
            concept_id = item["concept_id"]

            # Validate and insert question into gen_questions table
            gen_question_insert = GenQuestionsInsert(**question_data)
            result = (
                supabase_client.table("gen_questions")
                .insert(gen_question_insert.model_dump(mode="json", exclude_none=True))
                .execute()
            )

            if result.data:
                inserted_question = result.data[0]
                question_id = inserted_question["id"]

                # Create concept-question mapping
                concept_map = GenQuestionsConceptsMapsInsert(
                    gen_question_id=question_id,
                    concept_id=concept_id,
                )
                supabase_client.table("gen_questions_concepts_maps").insert(
                    concept_map.model_dump(mode="json", exclude_none=True)
                ).execute()

        return Response(status_code=status.HTTP_201_CREATED)

    except Exception as e:
        logger.error(f"Error generating questions: {str(e)}", exc_info=True)
        return Response(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

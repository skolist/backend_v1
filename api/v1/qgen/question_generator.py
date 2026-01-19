"""
Consolidated Question Generator API
All question generation logic in one place - schemas, prompts, and endpoint.
"""

import asyncio
import json
import os
import logging
import uuid
from typing import List, Literal, Dict, Optional

from google import genai
from .utils.retry import generate_content_with_retries
from fastapi import Depends, status
from fastapi.responses import Response
from pydantic import BaseModel, Field, model_validator
import supabase

from api.v1.auth import get_supabase_client
from supabase_dir import (
    PublicHardnessLevelEnumEnum,
    GenQuestionsInsert,
    GenQuestionsConceptsMapsInsert,
)

from .utils.batchification import build_batches_end_to_end, Batch
from .models import (
    AllQuestions,
    QUESTION_TYPE_TO_SCHEMA,
    QUESTION_TYPE_TO_ENUM,
)

logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION SCHEMAS
# ============================================================================


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

    @model_validator(mode="after")
    def check_total_questions(self) -> "QuestionConfig":
        """Ensure total questions across all types is between 1 and 50."""
        total = sum(q.count for q in self.question_types)
        if total < 1 or total > 50:
            raise ValueError("Total number of questions must be between 1 and 50.")
        return self


class GenerateQuestionsRequest(BaseModel):
    """Generate Questions Request."""

    activity_id: uuid.UUID
    concept_ids: List[uuid.UUID]
    config: QuestionConfig
    # Optional custom instructions/prompt forwarded from the frontend UI
    instructions: Optional[str] = None


# ============================================================================
# PROMPT FUNCTIONS
# ============================================================================


def generate_questions_prompt(
    concepts: List[str],
    concepts_descriptions: Dict[str, str],
    old_questions_on_concepts: List[AllQuestions],
    n: int,
    question_type: str,
    difficulty: str,
    instructions: Optional[str] = None,
) -> str:
    """Generate prompt for creating questions for a batch of concepts."""

    # Build concept information
    concept_info = []
    for concept in concepts:
        desc = concepts_descriptions.get(concept, "No description available")
        concept_info.append(f"{concept}: {desc}")

    concepts_text = "\n".join(concept_info)

    prompt = """
    You have access to these concepts and their descriptions:
    {concepts_text}
    
    Historical questions for reference: {old_questions_on_concepts}
    
    Generate {n} questions of type {question_type} with difficulty level: {difficulty}
    
    Instructions:
    - Choose concepts from the provided list above that are most relevant for each question
    - The questions should align with the specified difficulty level: {difficulty}
    - Use patterns from historical questions as reference but create original questions
    - Be strictly within the knowledge of the provided concepts, no external knowledge
    - Strictly use LaTeX format for mathematical entities like symbols and formulas
    - Strictly output all required fields for the question schema. Answer Text is mandatory, use LaTeX where needed
    - Question should  be Strictly Accurate and High Quality
    {instructions_block}
    """

    instructions_block = (
        f"\nAdditional user instructions (prioritize these): {instructions}"
        if instructions
        else ""
    )

    return prompt.format(
        concepts_text=concepts_text,
        old_questions_on_concepts=old_questions_on_concepts,
        n=n,
        question_type=question_type,
        difficulty=difficulty,
        instructions_block=instructions_block,
    )


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def extract_question_type_counts_dict(
    request: GenerateQuestionsRequest,
) -> Dict[str, int]:
    """Extract question type counts as dictionary from the request."""
    return {qt.type: qt.count for qt in request.config.question_types if qt.count > 0}


def extract_difficulty_percentages(
    difficulty_distribution: DifficultyDistribution,
) -> Dict[str, float]:
    """Convert difficulty distribution to percentages."""
    return {
        "easy": difficulty_distribution.easy,
        "medium": difficulty_distribution.medium,
        "hard": difficulty_distribution.hard,
    }


# ============================================================================
# CORE LOGIC FUNCTIONS (No Supabase dependency)
# ============================================================================


async def generate_questions_for_batches(
    gemini_client: genai.Client,
    batches: List[Batch],
    concepts_dict: Dict[str, str],
    concepts_name_to_id: Dict[str, str],
    old_questions: List[dict],
    activity_id: uuid.UUID,
    default_marks: int = 1,
) -> List[Dict[str, any]]:
    """
    Generate questions based on batches using GenAI.

    Uses async parallelization to make concurrent API calls for each batch,
    significantly reducing total execution time for network-bound operations.

    Args:
        gemini_client: Initialized Gemini client
        batches: List of batches with question requirements
        concepts_dict: Mapping of concept name to description
        concepts_name_to_id: Mapping of concept name to concept ID
        old_questions: List of historical questions for reference
        activity_id: UUID of the activity these questions belong to
        default_marks: Default marks for generated questions

    Returns:
        List of dicts with 'question' (GenQuestionsInsert-compatible) and 'concept_ids'
    """

    async def generate_questions_for_batch(
        batch: Batch,
    ) -> List[Dict[str, any]]:
        """Generate questions for a specific batch."""
        question_schema = QUESTION_TYPE_TO_SCHEMA.get(batch.question_type)
        question_type_enum = QUESTION_TYPE_TO_ENUM.get(batch.question_type)

        if not question_schema or not question_type_enum:
            logger.warning(f"Unknown question type: {batch.question_type}")
            return []

        # Deduplicate concepts for this batch
        unique_concepts = list(
            dict.fromkeys(batch.concepts)
        )  # Preserves order while removing duplicates

        # Map difficulty to enum
        difficulty_mapping = {
            "easy": PublicHardnessLevelEnumEnum.EASY,
            "medium": PublicHardnessLevelEnumEnum.MEDIUM,
            "hard": PublicHardnessLevelEnumEnum.HARD,
        }
        hardness_level = difficulty_mapping.get(
            batch.difficulty, PublicHardnessLevelEnumEnum.MEDIUM
        )

        try:
            # Use async API call for parallel execution
            questions_response = await generate_content_with_retries(
                gemini_client=gemini_client,
                model="gemini-3-flash-preview",
                contents=generate_questions_prompt(
                    concepts=unique_concepts,
                    concepts_descriptions=concepts_dict,
                    old_questions_on_concepts=old_questions,
                    n=batch.n_questions,
                    question_type=batch.question_type,
                    difficulty=batch.difficulty,
                    instructions=batch.custom_instruction,
                ),
                config={
                    "response_mime_type": "application/json",
                    "response_schema": question_schema,
                },
                retries=5,
            )

            results = []

            # Get the question model class for individual validation
            question_model = question_schema.__annotations__.get(
                "questions"
            ).__args__[0]

            # Try to get parsed questions, fall back to raw JSON if parsing fails
            try:
                questions_list = questions_response.parsed.questions
            except Exception as parse_error:
                logger.warning(
                    f"Failed to parse full response, attempting raw JSON parsing: {parse_error}"
                )
                # Fall back to parsing raw JSON response
                raw_text = questions_response.text
                raw_data = json.loads(raw_text)
                questions_list = raw_data.get("questions", [])

            for q in questions_list:
                try:
                    # If q is already a Pydantic model, use it directly
                    if hasattr(q, "model_dump"):
                        question_data = q.model_dump()
                    else:
                        # Validate individual question with Pydantic model
                        validated_q = question_model.model_validate(q)
                        question_data = validated_q.model_dump()

                    # Skip questions missing the essential field (question_text)
                    if not question_data.get("question_text"):
                        logger.warning(
                            f"Skipping question with missing question_text: {question_data}"
                        )
                        continue

                    gen_question_dict = {
                        **question_data,
                        "activity_id": str(activity_id),
                        "question_type": question_type_enum,
                        "hardness_level": hardness_level,
                        "marks": default_marks,
                    }
                    # Collect unique concept IDs for this batch
                    concept_ids = list(
                        dict.fromkeys(
                            [  # Remove duplicates while preserving order
                                concepts_name_to_id.get(concept)
                                for concept in unique_concepts
                                if concepts_name_to_id.get(concept)
                            ]
                        )
                    )
                    results.append(
                        {
                            "question": gen_question_dict,
                            "concept_ids": concept_ids,
                        }
                    )
                except Exception as validation_error:
                    logger.warning(
                        f"Skipping invalid question due to validation error: {validation_error}. "
                        f"Question data: {q}"
                    )
                    continue

            return results
        except Exception as e:
            logger.error(
                f"Error parsing questions response for batch {batch}: {e}",
                exc_info=True,
            )
            return []

    # Execute all batch API calls in parallel
    tasks = [generate_questions_for_batch(batch) for batch in batches]
    results = await asyncio.gather(*tasks)

    # Flatten results
    gen_questions_data: List[Dict[str, any]] = []
    for result in results:
        gen_questions_data.extend(result)

    return gen_questions_data


# ============================================================================
# API ENDPOINT (Wrapper with Supabase integration)
# ============================================================================


async def generate_questions(
    request: GenerateQuestionsRequest,
    supabase_client: supabase.Client = Depends(get_supabase_client),
) -> Response:
    """
    Generate questions based on concepts and configuration.

    This endpoint orchestrates:
    1. Fetches concepts and historical questions from Supabase
    2. Calls generate_distribution() to get question distribution
    3. Calls generate_questions_for_distribution() to create questions (parallelized)
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
        # QUESTION GENERATION (Batchified Logic)
        # ====================================================================

        # Extract parameters for batchification
        question_type_counts = extract_question_type_counts_dict(request)
        difficulty_percentages = extract_difficulty_percentages(
            request.config.difficulty_distribution
        )
        concept_names = [concept["name"] for concept in concepts]

        # Create batches using batchification logic
        batches = build_batches_end_to_end(
            question_type_counts=question_type_counts,
            concepts=concept_names,
            difficulty_percent=difficulty_percentages,
            custom_instruction=request.instructions,
            max_questions_per_batch=3,
            seed=None,
            shuffle_input_concepts=True,
            custom_instruction_fraction=0.30,
            custom_instruction_mode="first",
        )

        # Initialize Gemini client
        gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

        # Generate questions for all batches (parallelized)
        gen_questions_data = await generate_questions_for_batches(
            gemini_client=gemini_client,
            batches=batches,
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
            concept_ids = item["concept_ids"]

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

                # Create concept-question mappings for all unique concepts in the batch
                for concept_id in concept_ids:
                    try:
                        concept_map = GenQuestionsConceptsMapsInsert(
                            gen_question_id=question_id,
                            concept_id=concept_id,
                        )
                        supabase_client.table("gen_questions_concepts_maps").insert(
                            concept_map.model_dump(mode="json", exclude_none=True)
                        ).execute()
                    except Exception as mapping_error:
                        # Handle duplicate key constraint violations (ignore duplicates)
                        if "duplicate key value violates unique constraint" in str(
                            mapping_error
                        ):
                            logger.info(
                                f"""
                        Concept-question mapping already exists for question_id={question_id},
                        concept_id={concept_id}. Skipping.
                                """
                            )
                        else:
                            # Re-raise if it's a different error
                            raise mapping_error

        return Response(status_code=status.HTTP_201_CREATED)

    except Exception as e:
        logger.error(f"Error generating questions: {str(e)}", exc_info=True)
        return Response(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

"""
Consolidated Question Generator API

Architecture:
    1. batchify_request() - Creates batches from API request
    2. process_batch_generation() - Single Gemini call for one batch (no retries)
    3. process_batch_generation_and_validate() - Wrapper that validates the generated questions
    4. try_retry_batch() - Retry wrapper with configurable max retries
    5. insert_batch_to_supabase() - Generates + inserts questions for one batch
    6. process_all_batches() - Parallel execution of all batches with immediate DB insertion
"""

import asyncio
import json
import os
import logging
import uuid
from dataclasses import dataclass
from typing import List, Literal, Dict, Optional

from google import genai
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
from .prompts import generate_questions_prompt
from .credits import check_user_has_credits, deduct_user_credits
from api.v1.auth import require_supabase_user

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
# BATCH CONTEXT - Holds all data needed for batch processing
# ============================================================================


@dataclass
class BatchProcessingContext:
    """
    Holds all contextual data needed for processing batches.

    This avoids passing many parameters through the function chain.
    """

    gemini_client: genai.Client
    concepts_dict: Dict[str, str]  # concept_name -> description
    concepts_name_to_id: Dict[str, str]  # concept_name -> concept_id
    old_questions: List[dict]  # historical questions for reference
    activity_id: uuid.UUID
    default_marks: int = 1


# ============================================================================
# CUSTOM EXCEPTIONS
# ============================================================================


class BatchGenerationError(Exception):
    """Raised when batch generation fails after all retries."""

    pass


class BatchValidationError(Exception):
    """Raised when generated questions fail validation."""

    pass


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
# STEP 1: BATCHIFICATION
# ============================================================================


def batchify_request(
    request: GenerateQuestionsRequest,
    concept_names: List[str],
) -> List[Batch]:
    """
    Convert API request into a list of batches for parallel processing.

    Takes the question generation request and breaks it down into smaller
    batches that can be processed independently and in parallel.

    Args:
        request: The incoming API request with question configuration
        concept_names: List of concept names fetched from database

    Returns:
        List of Batch objects ready for parallel processing
    """
    logger.debug(
        "Starting batchification",
        extra={
            "concept_count": len(concept_names),
            "activity_id": str(request.activity_id),
        },
    )

    # Extract parameters for batchification
    question_type_counts = extract_question_type_counts_dict(request)
    difficulty_percentages = extract_difficulty_percentages(
        request.config.difficulty_distribution
    )

    logger.debug(
        "Batchification parameters extracted",
        extra={
            "question_type_counts": question_type_counts,
            "difficulty_percentages": difficulty_percentages,
        },
    )

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

    logger.debug(
        "Batches created",
        extra={"batch_count": len(batches)},
    )
    return batches


# ============================================================================
# STEP 2: SINGLE BATCH GENERATION (No Retries)
# ============================================================================


async def process_batch_generation(
    batch: Batch,
    ctx: BatchProcessingContext,
    batch_idx: int = None,
    retry_idx: int = None,
) -> dict:
    """
    Generate questions for a single batch by calling Gemini API once.

    This function makes a single API call without any retry logic.
    It returns the raw response from Gemini for further processing.

    Args:
        batch: The batch containing question requirements
        ctx: Processing context with client and reference data
        batch_idx: Index of the batch (for logging)
        retry_idx: Current retry attempt number (for logging)

    Returns:
        Raw response dict from Gemini API

    Raises:
        BatchGenerationError: If the API call fails or returns invalid response
    """
    prefix = _log_prefix(batch_idx, retry_idx)

    logger.debug(
        "Processing batch",
        extra={
            "batch_idx": batch_idx,
            "retry_idx": retry_idx,
            "question_type": batch.question_type,
            "difficulty": batch.difficulty,
            "n_questions": batch.n_questions,
        },
    )

    # Get schema for this question type
    question_schema = QUESTION_TYPE_TO_SCHEMA.get(batch.question_type)

    if not question_schema:
        raise BatchGenerationError(f"Unknown question type: {batch.question_type}")

    # Deduplicate concepts for this batch
    unique_concepts = list(dict.fromkeys(batch.concepts))
    logger.debug(
        "Unique concepts for batch",
        extra={
            "batch_idx": batch_idx,
            "unique_concepts": unique_concepts,
        },
    )

    # Build the prompt
    prompt = generate_questions_prompt(
        concepts=unique_concepts,
        concepts_descriptions=ctx.concepts_dict,
        old_questions_on_concepts=ctx.old_questions,
        n=batch.n_questions,
        question_type=batch.question_type,
        difficulty=batch.difficulty,
        instructions=batch.custom_instruction,
    )

    logger.debug(
        "Making Gemini API call",
        extra={
            "batch_idx": batch_idx,
            "retry_idx": retry_idx,
        },
    )

    # Single API call - no retries here
    response = await ctx.gemini_client.aio.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config={
            "response_mime_type": "application/json",
            "response_schema": question_schema,
        },
    )

    logger.debug(
        "Gemini API call completed",
        extra={
            "batch_idx": batch_idx,
            "retry_idx": retry_idx,
            "status": "success",
        },
    )

    return {
        "response": response,
        "batch": batch,
        "unique_concepts": unique_concepts,
    }


# ============================================================================
# STEP 3: BATCH GENERATION + VALIDATION
# ============================================================================


async def process_batch_generation_and_validate(
    batch: Batch,
    ctx: BatchProcessingContext,
    batch_idx: int = None,
    retry_idx: int = None,
) -> List[Dict[str, any]]:
    """
    Generate questions for a batch and validate each question.

    Calls process_batch_generation() and then validates each question
    against the Pydantic schema. Invalid questions are filtered out.

    Args:
        batch: The batch containing question requirements
        ctx: Processing context with client and reference data
        batch_idx: Index of the batch (for logging)
        retry_idx: Current retry attempt number (for logging)

    Returns:
        List of validated question dicts with 'question' and 'concept_ids' keys

    Raises:
        BatchValidationError: If no valid questions could be generated
        BatchGenerationError: If the API call itself fails
    """
    prefix = _log_prefix(batch_idx, retry_idx)

    logger.debug(
        "Starting generation and validation",
        extra={
            "batch_idx": batch_idx,
            "retry_idx": retry_idx,
            "question_type": batch.question_type,
        },
    )

    # Step 1: Generate questions
    generation_result = await process_batch_generation(batch, ctx, batch_idx, retry_idx)

    response = generation_result["response"]
    unique_concepts = generation_result["unique_concepts"]

    # Get schema and enum for validation
    question_schema = QUESTION_TYPE_TO_SCHEMA.get(batch.question_type)
    question_type_enum = QUESTION_TYPE_TO_ENUM.get(batch.question_type)

    # Get the question model class for individual validation
    question_model = question_schema.__annotations__.get("questions").__args__[0]

    # Map difficulty to enum
    difficulty_mapping = {
        "easy": PublicHardnessLevelEnumEnum.EASY,
        "medium": PublicHardnessLevelEnumEnum.MEDIUM,
        "hard": PublicHardnessLevelEnumEnum.HARD,
    }
    hardness_level = difficulty_mapping.get(
        batch.difficulty, PublicHardnessLevelEnumEnum.MEDIUM
    )

    # Step 2: Parse response
    logger.debug(
        "Parsing Gemini response",
        extra={
            "batch_idx": batch_idx,
            "retry_idx": retry_idx,
        },
    )

    try:
        questions_list = response.parsed.questions
        logger.debug(
            "Parsed questions from response",
            extra={
                "batch_idx": batch_idx,
                "retry_idx": retry_idx,
                "question_count": len(questions_list),
            },
        )
    except Exception as parse_error:
        logger.warning(
            "Failed to parse structured response, attempting raw JSON",
            extra={
                "batch_idx": batch_idx,
                "retry_idx": retry_idx,
                "error": str(parse_error),
            },
        )
        # Fall back to parsing raw JSON response
        raw_text = response.text
        raw_data = json.loads(raw_text)
        questions_list = raw_data.get("questions", [])
        logger.debug(
            "Parsed questions from raw JSON",
            extra={
                "batch_idx": batch_idx,
                "retry_idx": retry_idx,
                "question_count": len(questions_list),
            },
        )
        raise

    # Step 3: Validate each question
    validated_questions = []

    for idx, q in enumerate(questions_list):
        logger.debug(
            "Validating question",
            extra={
                "batch_idx": batch_idx,
                "retry_idx": retry_idx,
                "question_idx": idx + 1,
                "total_questions": len(questions_list),
            },
        )

        try:
            # If q is already a Pydantic model, use it directly
            if hasattr(q, "model_dump"):
                question_data = q.model_dump()
            else:
                # Validate individual question with Pydantic model
                validated_q = question_model.model_validate(q)
                question_data = validated_q.model_dump()

            # raise if missing the essential field (question_text)
            if not question_data.get("question_text"):
                logger.warning(
                    "Question missing question_text, skipping",
                    extra={
                        "batch_idx": batch_idx,
                        "retry_idx": retry_idx,
                        "question_idx": idx + 1,
                    },
                )
                raise

            # Build the final question dict
            gen_question_dict = {
                **question_data,
                "activity_id": str(ctx.activity_id),
                "question_type": question_type_enum,
                "hardness_level": hardness_level,
                "marks": ctx.default_marks,
            }

            # Collect unique concept IDs for this batch
            concept_ids = list(
                dict.fromkeys(
                    [
                        ctx.concepts_name_to_id.get(concept)
                        for concept in unique_concepts
                        if ctx.concepts_name_to_id.get(concept)
                    ]
                )
            )

            validated_questions.append(
                {
                    "question": gen_question_dict,
                    "concept_ids": concept_ids,
                }
            )
            logger.debug(
                "Question validated successfully",
                extra={
                    "batch_idx": batch_idx,
                    "retry_idx": retry_idx,
                    "question_idx": idx + 1,
                },
            )

        except Exception as validation_error:
            logger.warning(
                "Question validation failed, skipping",
                extra={
                    "batch_idx": batch_idx,
                    "retry_idx": retry_idx,
                    "question_idx": idx + 1,
                    "error": str(validation_error),
                },
            )
            continue

    # Check if we got any valid questions
    if not validated_questions:
        raise BatchValidationError(
            f"No valid questions generated for batch: {batch.question_type}"
        )

    logger.debug(
        "Batch validation complete",
        extra={
            "batch_idx": batch_idx,
            "retry_idx": retry_idx,
            "valid_count": len(validated_questions),
            "total_count": len(questions_list),
        },
    )

    return validated_questions


# ============================================================================
# STEP 4: RETRY WRAPPER
# ============================================================================


def _log_prefix(batch_idx: int = None, retry_idx: int = None) -> str:
    """
    Generate consistent log prefix with BATCH and RETRY info.

    Format: "BATCH:X RETRY:Y |" or "BATCH:X |" or empty string
    """
    parts = []
    if batch_idx is not None:
        parts.append(f"BATCH:{batch_idx}")
    if retry_idx is not None:
        parts.append(f"RETRY:{retry_idx}")
    return f"{' '.join(parts)} | " if parts else ""


async def try_retry_batch(
    batch: Batch,
    batch_idx: int,
    ctx: BatchProcessingContext,
    max_retries: int = 3,
) -> List[Dict[str, any]]:
    """
    Attempt to generate and validate a batch with retry logic.

    Wraps process_batch_generation_and_validate() with configurable retries.
    On failure, logs the error and retries until max_retries is reached.

    Args:
        batch: The batch to process
        batch_idx : Index of the batch to process
        ctx: Processing context with client and reference data
        max_retries: Maximum number of retry attempts (default: 3)

    Returns:
        List of validated question dicts

    Raises:
        BatchGenerationError: If all retry attempts fail
    """
    logger.debug(
        "Starting retry wrapper",
        extra={
            "batch_idx": batch_idx,
            "max_retries": max_retries,
        },
    )

    last_exception = None

    for attempt in range(max_retries):
        retry_idx = attempt + 1

        try:
            logger.debug(
                "Starting retry attempt",
                extra={
                    "batch_idx": batch_idx,
                    "retry_idx": retry_idx,
                    "max_retries": max_retries,
                },
            )

            result = await process_batch_generation_and_validate(
                batch, ctx, batch_idx, retry_idx
            )

            logger.debug(
                "Batch succeeded",
                extra={
                    "batch_idx": batch_idx,
                    "retry_idx": retry_idx,
                    "question_count": len(result),
                },
            )
            return result

        except Exception as e:
            last_exception = e

            if attempt < max_retries - 1:
                # Not the last attempt, log and continue
                logger.warning(
                    "Attempt failed, retrying",
                    extra={
                        "batch_idx": batch_idx,
                        "retry_idx": retry_idx,
                        "error": str(e),
                    },
                )
            else:
                # Last attempt failed
                logger.error(
                    "All retry attempts exhausted",
                    extra={
                        "batch_idx": batch_idx,
                        "max_retries": max_retries,
                        "final_error": str(e),
                    },
                )

    # All retries exhausted
    raise BatchGenerationError(
        f"Batch generation failed after {max_retries} retries"
    ) from last_exception


# ============================================================================
# STEP 5: INSERT BATCH TO SUPABASE
# ============================================================================


async def insert_batch_to_supabase(
    batch: Batch,
    batch_idx: int,
    ctx: BatchProcessingContext,
    supabase_client: supabase.Client,
    max_retries: int = 3,
) -> int:
    """
    Generate questions for a batch and immediately insert into Supabase.

    This is the per-batch worker function that:
    1. Generates and validates questions using try_retry_batch()
    2. Inserts each question into gen_questions table
    3. Creates concept-question mappings

    Questions are inserted as soon as they're ready, enabling faster
    availability to end users.

    Args:
        batch: The batch to process
        batch_idx : Index of the batch to process
        ctx: Processing context with client and reference data
        supabase_client: Supabase client for database operations
        max_retries: Maximum retry attempts for generation

    Returns:
        Number of questions successfully inserted
    
    Raises:
        BatchGenerationError: If generation fails after all retries
    """
    prefix = _log_prefix(batch_idx)
    logger.debug(
        "Starting insert_batch_to_supabase",
        extra={
            "batch_idx": batch_idx,
            "question_type": batch.question_type,
        },
    )

    # Step 1: Generate and validate questions with retries
    questions = await try_retry_batch(batch, batch_idx, ctx, max_retries)

    logger.debug(
        "Validated questions ready for DB insertion",
        extra={
            "batch_idx": batch_idx,
            "question_count": len(questions),
        },
    )

    inserted_count = 0

    # Step 2: Insert each question into database
    for idx, item in enumerate(questions):
        question_data = item["question"]
        concept_ids = item["concept_ids"]

        logger.debug(
            "Inserting question into gen_questions",
            extra={
                "batch_idx": batch_idx,
                "question_idx": idx + 1,
                "total_questions": len(questions),
            },
        )

        # Validate with GenQuestionsInsert schema before insert
        gen_question_insert = GenQuestionsInsert(**question_data)

        result = (
            supabase_client.table("gen_questions")
            .insert(gen_question_insert.model_dump(mode="json", exclude_none=True))
            .execute()
        )

        if result.data:
            inserted_question = result.data[0]
            question_id = inserted_question["id"]
            inserted_count += 1

            logger.debug(
                "Question inserted",
                extra={
                    "batch_idx": batch_idx,
                    "question_id": question_id,
                },
            )

            # Step 3: Create concept-question mappings
            for concept_id in concept_ids:
                try:
                    concept_map = GenQuestionsConceptsMapsInsert(
                        gen_question_id=question_id,
                        concept_id=concept_id,
                    )
                    supabase_client.table("gen_questions_concepts_maps").insert(
                        concept_map.model_dump(mode="json", exclude_none=True)
                    ).execute()

                    logger.debug(
                        "Created concept-question mapping",
                        extra={
                            "batch_idx": batch_idx,
                            "question_id": question_id,
                            "concept_id": concept_id,
                        },
                    )

                except Exception as mapping_error:
                    # Handle duplicate key constraint violations gracefully
                    if "duplicate key value violates unique constraint" in str(
                        mapping_error
                    ):
                        logger.debug(
                            "Mapping already exists, skipping",
                            extra={
                                "batch_idx": batch_idx,
                                "question_id": question_id,
                                "concept_id": concept_id,
                            },
                        )
                    else:
                        # Log but don't fail the entire batch for mapping errors
                        logger.warning(
                            "Failed to create concept-question mapping",
                            extra={
                                "batch_idx": batch_idx,
                                "question_id": question_id,
                                "concept_id": concept_id,
                                "error": str(mapping_error),
                            },
                        )

    logger.debug(
        "Batch insertion complete",
        extra={
            "batch_idx": batch_idx,
            "questions_inserted": inserted_count,
        },
    )
    return inserted_count


# ============================================================================
# STEP 6: PROCESS ALL BATCHES IN PARALLEL
# ============================================================================


async def process_all_batches(
    batches: List[Batch],
    ctx: BatchProcessingContext,
    supabase_client: supabase.Client,
    max_retries: int = 3,
) -> Dict[str, any]:
    """
    Process all batches in parallel with immediate database insertion.

    Runs insert_batch_to_supabase() for each batch concurrently using
    asyncio.gather(). Questions are inserted into the database as soon
    as each batch completes, enabling faster availability to users.

    Failed batches are logged but don't stop other batches from completing.

    Args:
        batches: List of batches to process
        ctx: Processing context with client and reference data
        supabase_client: Supabase client for database operations
        max_retries: Maximum retry attempts per batch

    Returns:
        Dict with 'successful' count, 'failed' count, and 'questions_inserted' count
    """
    logger.debug(
        "Starting parallel batch processing",
        extra={"batch_count": len(batches)},
    )

    # Create tasks for all batches
    tasks = [
        insert_batch_to_supabase(
            batch, batch_idx + 1, ctx, supabase_client, max_retries
        )
        for batch_idx, batch in enumerate(batches)
    ]

    # Run all batches in parallel, return_exceptions=True to not fail fast
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Count successes, failures, and inserted questions
    successful = 0
    failed = 0
    questions_inserted = 0

    for idx, result in enumerate(results):
        batch_idx = idx + 1
        if isinstance(result, Exception):
            failed += 1
            logger.error(
                "Batch failed",
                extra={
                    "batch_idx": batch_idx,
                    "error": str(result),
                },
            )
        else:
            successful += 1
            # Result of insert_batch_to_supabase is the number of questions inserted (int)
            questions_inserted += result if isinstance(result, int) else 0
            
            logger.debug(
                "Batch completed successfully",
                extra={
                    "batch_idx": batch_idx, 
                    "questions_count": result if isinstance(result, int) else "unknown"
                },
            )

    logger.info(
        "All batches processed",
        extra={
            "successful_batches": successful,
            "failed_batches": failed,
            "total_batches": len(batches),
            "questions_inserted": questions_inserted,
        },
    )

    return {
        "successful": successful,
        "failed": failed,
        "total": len(batches),
        "questions_inserted": questions_inserted,
    }


# ============================================================================
# API ENDPOINT
# ============================================================================


async def generate_questions(
    request: GenerateQuestionsRequest,
    supabase_client: supabase.Client = Depends(get_supabase_client),
    user: dict = Depends(require_supabase_user),
) -> Response:
    """
    Generate questions based on concepts and configuration.

    This endpoint orchestrates the question generation pipeline:
    1. Fetches concepts and historical questions from Supabase
    2. Batchifies the request into smaller parallel units
    3. Processes all batches in parallel
    4. Each batch inserts questions immediately upon completion

    Questions become available in the database as soon as each batch
    completes, rather than waiting for all batches to finish.

    Args:
        request: The question generation request
        supabase_client: Injected Supabase client
        user: The authenticated user

    Returns:
        201 Created on success
        500 Internal Server Error on failure
    """
    try:
        user_id = user.id
        
        # Check if user has credits
        if not check_user_has_credits(user_id):
            logger.warning(f"User {user_id} has insufficient credits to generate questions.")
            return Response(status_code=status.HTTP_402_PAYMENT_REQUIRED, content="Insufficient credits")

        logger.info(
            "Received generate_questions request",
            extra={
                "activity_id": str(request.activity_id),
                "concept_count": len(request.concept_ids),
                "user_id": str(user_id),
            },
        )

        # ====================================================================
        # DATA FETCHING (Supabase)
        # ====================================================================

        logger.debug(
            "Fetching concepts from database",
            extra={"activity_id": str(request.activity_id)},
        )

        # Fetch concepts from the database
        concepts = (
            supabase_client.table("concepts")
            .select("id, name, description")
            .in_("id", [str(cid) for cid in request.concept_ids])
            .execute()
            .data
        )

        logger.debug(
            "Fetched concepts",
            extra={
                "activity_id": str(request.activity_id),
                "concept_count": len(concepts),
            },
        )

        concepts_dict = {
            concept["name"]: concept["description"] for concept in concepts
        }
        concepts_name_to_id = {concept["name"]: concept["id"] for concept in concepts}

        # Fetch old questions for reference
        logger.debug(
            "Fetching historical questions",
            extra={"activity_id": str(request.activity_id)},
        )

        concept_maps = (
            supabase_client.table("bank_questions_concepts_maps")
            .select("bank_question_id")
            .in_("concept_id", [str(cid) for cid in request.concept_ids])
            .execute()
            .data
        )
        bank_question_ids = list({m["bank_question_id"] for m in concept_maps})

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

        logger.debug(
            "Fetched historical questions",
            extra={
                "activity_id": str(request.activity_id),
                "historical_question_count": len(old_questions),
            },
        )

        # ====================================================================
        # BATCHIFICATION
        # ====================================================================

        concept_names = [concept["name"] for concept in concepts]
        batches = batchify_request(request, concept_names)

        logger.debug(
            "Batches created for processing",
            extra={
                "activity_id": str(request.activity_id),
                "batch_count": len(batches),
            },
        )

        # ====================================================================
        # INITIALIZE CONTEXT
        # ====================================================================

        gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

        ctx = BatchProcessingContext(
            gemini_client=gemini_client,
            concepts_dict=concepts_dict,
            concepts_name_to_id=concepts_name_to_id,
            old_questions=old_questions,
            activity_id=request.activity_id,
        )

        logger.debug(
            "BatchProcessingContext initialized",
            extra={"activity_id": str(request.activity_id)},
        )

        # ====================================================================
        # PARALLEL BATCH PROCESSING WITH IMMEDIATE INSERTION
        # ====================================================================

        result = await process_all_batches(
            batches=batches,
            ctx=ctx,
            supabase_client=supabase_client,
            max_retries=3,
        )
        
        # Calculate credits to deduct (5 credits per inserted question)
        questions_inserted = result.get("questions_inserted", 0)
        credits_to_deduct = questions_inserted * 5
        
        if credits_to_deduct > 0:
            deduct_user_credits(user_id, credits_to_deduct)

        logger.info(
            "Question generation complete",
            extra={
                "activity_id": str(request.activity_id),
                "successful_batches": result["successful"],
                "failed_batches": result["failed"],
                "total_batches": result["total"],
                "questions_inserted": questions_inserted,
                "credits_deducted": credits_to_deduct,
            },
        )

        return Response(status_code=status.HTTP_201_CREATED)

    except Exception as e:
        logger.exception(
            "Error generating questions",
            extra={
                "activity_id": str(request.activity_id),
                "error": str(e),
                "error_type": type(e).__name__,
            },
        )
        return Response(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

import asyncio
import json
import os
import logging
import uuid
from dataclasses import dataclass
from typing import List, Dict, Optional, Any

from google import genai
import supabase

from supabase_dir import (
    PublicHardnessLevelEnumEnum,
    GenQuestionsInsert,
    GenQuestionsConceptsMapsInsert,
)

from .batchification import build_batches_end_to_end, Batch
from ..models import (
    QUESTION_TYPE_TO_ENUM,
)
from .models import QUESTION_TYPE_TO_SCHEMA_WITH_CONCEPTS
from ..prompts import generate_questions_with_concepts_prompt

logger = logging.getLogger(__name__)

@dataclass
class BatchProcessingContext:
    """Holds all contextual data needed for processing batches."""
    gemini_client: genai.Client
    concepts_dict: Dict[str, str]  # concept_name -> description
    concepts_name_to_id: Dict[str, str]  # concept_name -> concept_id
    old_questions: List[dict]  # historical questions for reference
    activity_id: uuid.UUID
    default_marks: int = 1

class BatchGenerationError(Exception):
    """Raised when batch generation fails after all retries."""
    pass

class BatchValidationError(Exception):
    """Raised when generated questions fail validation."""
    pass

def _log_prefix(batch_idx: int = None, retry_idx: int = None) -> str:
    parts = []
    if batch_idx is not None:
        parts.append(f"BATCH:{batch_idx}")
    if retry_idx is not None:
        parts.append(f"RETRY:{retry_idx}")
    return f"{' '.join(parts)} | " if parts else ""

async def process_batch_generation(
    batch: Batch,
    ctx: BatchProcessingContext,
    batch_idx: int = None,
    retry_idx: int = None,
) -> dict:
    prefix = _log_prefix(batch_idx, retry_idx)
    
    # Get schema for this question type (using the new schemas with concepts)
    question_schema = QUESTION_TYPE_TO_SCHEMA_WITH_CONCEPTS.get(batch.question_type)

    if not question_schema:
        raise BatchGenerationError(f"Unknown question type: {batch.question_type}")

    unique_concepts = list(dict.fromkeys(batch.concepts))
    logger.debug(f"{prefix}Processing batch with custom instructions: {batch.custom_instruction}")

    prompt = generate_questions_with_concepts_prompt(
        concepts=unique_concepts,
        concepts_descriptions=ctx.concepts_dict,
        old_questions_on_concepts=ctx.old_questions,
        n=batch.n_questions,
        question_type=batch.question_type,
        difficulty=batch.difficulty,
        instructions=batch.custom_instruction,
    )

    response = await ctx.gemini_client.aio.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config={
            "response_mime_type": "application/json",
            "response_schema": question_schema,
        },
    )

    return {
        "response": response,
        "batch": batch,
    }

async def process_batch_generation_and_validate(
    batch: Batch,
    ctx: BatchProcessingContext,
    batch_idx: int = None,
    retry_idx: int = None,
) -> List[Dict[str, any]]:
    generation_result = await process_batch_generation(batch, ctx, batch_idx, retry_idx)
    response = generation_result["response"]

    question_schema = QUESTION_TYPE_TO_SCHEMA_WITH_CONCEPTS.get(batch.question_type)
    question_type_enum = QUESTION_TYPE_TO_ENUM.get(batch.question_type)
    # The question model is the first argument of the List in the 'questions' annotation
    question_model = question_schema.__annotations__.get("questions").__args__[0]

    difficulty_mapping = {
        "easy": PublicHardnessLevelEnumEnum.EASY,
        "medium": PublicHardnessLevelEnumEnum.MEDIUM,
        "hard": PublicHardnessLevelEnumEnum.HARD,
    }
    hardness_level = difficulty_mapping.get(
        batch.difficulty, PublicHardnessLevelEnumEnum.MEDIUM
    )

    try:
        questions_list = response.parsed.questions
    except Exception:
        raw_text = response.text
        raw_data = json.loads(raw_text)
        questions_list = raw_data.get("questions", [])

    validated_questions = []

    for idx, q in enumerate(questions_list):
        try:
            if hasattr(q, "model_dump"):
                question_data = q.model_dump()
            else:
                validated_q = question_model.model_validate(q)
                question_data = validated_q.model_dump()

            if not question_data.get("question_text"):
                continue

            # Extract granular concepts returned by Gemini for THIS question
            question_concepts = question_data.pop("concepts", [])
            concept_ids = list(
                dict.fromkeys(
                    [
                        ctx.concepts_name_to_id.get(concept)
                        for concept in question_concepts
                        if ctx.concepts_name_to_id.get(concept)
                    ]
                )
            )

            # Fallback to batch concepts if Gemini didn't return any valid ones
            if not concept_ids:
                concept_ids = list(
                    dict.fromkeys(
                        [
                            ctx.concepts_name_to_id.get(concept)
                            for concept in batch.concepts
                            if ctx.concepts_name_to_id.get(concept)
                        ]
                    )
                )

            gen_question_dict = {
                **question_data,
                "activity_id": str(ctx.activity_id),
                "question_type": question_type_enum,
                "hardness_level": hardness_level,
                "marks": ctx.default_marks,
            }

            validated_questions.append(
                {
                    "question": gen_question_dict,
                    "concept_ids": concept_ids,
                }
            )

        except Exception as e:
            logger.warning(f"Question validation failed: {e}")
            continue

    if not validated_questions:
        raise BatchValidationError(
            f"No valid questions generated for batch: {batch.question_type}"
        )

    return validated_questions

async def try_retry_batch(
    batch: Batch,
    batch_idx: int,
    ctx: BatchProcessingContext,
    max_retries: int = 3,
) -> List[Dict[str, any]]:
    last_exception = None
    for attempt in range(max_retries):
        retry_idx = attempt + 1
        try:
            return await process_batch_generation_and_validate(
                batch, ctx, batch_idx, retry_idx
            )
        except Exception as e:
            last_exception = e
            if attempt >= max_retries - 1:
                logger.error(f"All retry attempts exhausted for batch {batch_idx}: {e}")

    raise BatchGenerationError(
        f"Batch generation failed after {max_retries} retries"
    ) from last_exception

async def insert_batch_to_supabase(
    batch: Batch,
    batch_idx: int,
    ctx: BatchProcessingContext,
    supabase_client: supabase.Client,
    max_retries: int = 3,
) -> int:
    questions = await try_retry_batch(batch, batch_idx, ctx, max_retries)
    inserted_count = 0

    for idx, item in enumerate(questions):
        question_data = item["question"]
        concept_ids = item["concept_ids"]

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
                    if "duplicate key value violates unique constraint" not in str(mapping_error):
                        logger.warning(f"Failed to create mapping: {mapping_error}")

    return inserted_count

async def process_all_batches(
    batches: List[Batch],
    ctx: BatchProcessingContext,
    supabase_client: supabase.Client,
    max_retries: int = 3,
) -> Dict[str, any]:
    tasks = [
        insert_batch_to_supabase(
            batch, batch_idx + 1, ctx, supabase_client, max_retries
        )
        for batch_idx, batch in enumerate(batches)
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    successful = 0
    failed = 0
    questions_inserted = 0

    for idx, result in enumerate(results):
        if isinstance(result, Exception):
            failed += 1
        else:
            successful += 1
            questions_inserted += result if isinstance(result, int) else 0

    return {
        "successful": successful,
        "failed": failed,
        "total": len(batches),
        "questions_inserted": questions_inserted,
    }

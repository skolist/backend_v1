import logging
import os
import uuid
from typing import Literal

import supabase
from fastapi import Depends, status
from fastapi.responses import Response
from google import genai
from pydantic import BaseModel, Field, model_validator

from api.v1.auth import get_supabase_client, require_supabase_user

from ..credits import check_user_has_credits, deduct_user_credits
from .batchification import Batch, build_batches_end_to_end
from .service import (
    BatchProcessingContext,
    process_all_batches,
)

logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION SCHEMAS
# ============================================================================


class QuestionTypeConfig(BaseModel):
    """Question Type Configuration for the request."""

    type: Literal[
        "mcq4",
        "short_answer",
        "long_answer",
        "true_false",
        "fill_in_the_blank",
        "msq4",
        "match_the_following",
        "solved_examples",
        "exercise_questions",
    ]
    count: int


class DifficultyDistribution(BaseModel):
    """Difficulty Distribution Configuration."""

    easy: int = Field(..., ge=0, le=100)
    medium: int = Field(..., ge=0, le=100)
    hard: int = Field(..., ge=0, le=100)


class QuestionConfig(BaseModel):
    """Question Configuration."""

    question_types: list[QuestionTypeConfig]
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
    concept_ids: list[uuid.UUID]
    config: QuestionConfig
    instructions: str | None = None


# ============================================================================
# HELPERS
# ============================================================================


def extract_question_type_counts_dict(request: GenerateQuestionsRequest) -> dict[str, int]:
    return {qt.type: qt.count for qt in request.config.question_types if qt.count > 0}


def extract_difficulty_percentages(
    difficulty_distribution: DifficultyDistribution,
) -> dict[str, float]:
    return {
        "easy": difficulty_distribution.easy,
        "medium": difficulty_distribution.medium,
        "hard": difficulty_distribution.hard,
    }


def batchify_request(request: GenerateQuestionsRequest, concept_names: list[str]) -> list[Batch]:
    question_type_counts = extract_question_type_counts_dict(request)
    difficulty_percentages = extract_difficulty_percentages(request.config.difficulty_distribution)

    return build_batches_end_to_end(
        question_type_counts=question_type_counts,
        concepts=concept_names,
        difficulty_percent=difficulty_percentages,
        custom_instruction=request.instructions,
        max_questions_per_batch=3,
        seed=None,
        shuffle_input_concepts=True,
        custom_instruction_fraction=0.3,  # Apply to all batches
        custom_instruction_mode="first",
    )


# ============================================================================
# ROUTE
# ============================================================================


async def generate_questions(
    request: GenerateQuestionsRequest,
    supabase_client: supabase.Client = Depends(get_supabase_client),
    user: dict = Depends(require_supabase_user),
) -> Response:
    """Generate questions based on concepts and configuration."""
    try:
        user_id = user.id

        if not check_user_has_credits(user_id):
            return Response(status_code=status.HTTP_402_PAYMENT_REQUIRED, content="Insufficient credits")

        logger.debug(f"Custom instruction received: {request.instructions}")

        # Fetch concepts
        def chunked(lst, size):
            for i in range(0, len(lst), size):
                yield lst[i : i + size]

        try:
            ids = [str(cid) for cid in request.concept_ids if cid]
            concepts = []

            for batch in chunked(ids, 300):
                response = supabase_client.table("concepts").select("id, name, description").in_("id", batch).execute()
                concepts.extend(response.data or [])
        except Exception as e:
            logger.exception(f"Error fetching concepts: {e}")
            return Response(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

        concepts_dict = {concept["name"]: concept["description"] for concept in concepts}
        concepts_name_to_id = {concept["name"]: concept["id"] for concept in concepts}

        # Fetch historical questions for reference
        try:
            ids = [str(cid) for cid in request.concept_ids if cid]
            concept_maps = []

            for batch in chunked(ids, 300):
                response = (
                    supabase_client.table("bank_questions_concepts_maps")
                    .select("bank_question_id")
                    .in_("concept_id", batch)
                    .execute()
                )
                concept_maps.extend(response.data or [])
        except Exception as e:
            logger.warning(f"Error Fetching the concept maps: {e}")
            concept_maps = []

        bank_question_ids = list({m["bank_question_id"] for m in concept_maps})

        if bank_question_ids:
            try:
                old_questions = []
                for batch in chunked(bank_question_ids, 300):
                    response = supabase_client.table("bank_questions").select("*").in_("id", batch).execute()
                    old_questions.extend(response.data or [])
            except Exception as e:
                logger.warning(f"Error Fetching the old questions: {e}")
                old_questions = []
        else:
            old_questions = []

        # Batchification
        concept_names = [concept["name"] for concept in concepts]
        batches = batchify_request(request, concept_names)

        logger.debug(f"Total batches created: {len(batches)}")

        # Initialize context
        gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

        ctx = BatchProcessingContext(
            gemini_client=gemini_client,
            supabase_client=supabase_client,
            concepts_dict=concepts_dict,
            concepts_name_to_id=concepts_name_to_id,
            old_questions=old_questions,
            activity_id=request.activity_id,
        )

        # Process all batches
        result = await process_all_batches(
            batches=batches,
            ctx=ctx,
            supabase_client=supabase_client,
            max_retries=3,
        )

        # Credits deduction
        questions_inserted = result.get("questions_inserted", 0)
        credits_to_deduct = questions_inserted * 5

        if credits_to_deduct > 0:
            deduct_user_credits(user_id, credits_to_deduct)

        return Response(status_code=status.HTTP_201_CREATED)

    except Exception as e:
        logger.exception(f"Error generating questions: {e}")
        return Response(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

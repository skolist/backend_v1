import logging
import random
from enum import Enum
from typing import Any

import supabase

logger = logging.getLogger(__name__)

# Flags to control filtering of bank questions
USE_IMAGE_NEEDED = False  # If False, exclude questions with is_image_needed=True
USE_INCOMPLETE = False  # If False, exclude questions with is_incomplete=True


class QuestionRequestType(Enum):
    SOLVED_EXAMPLE = "solved_example"
    EXERCISE_QUESTION = "exercise_question"


def extract_bank_question_to_gen_payload(
    bank_question: dict[str, Any], request_type: QuestionRequestType
) -> dict[str, Any]:
    """
    Maps a bank_question row to the payload expected by gen_questions table.
    """
    # Base mapping
    payload = {
        "question_text": bank_question.get("question_text"),
        "answer_text": bank_question.get(
            "answer_text", ""
        ),  # Ensure answer_text is at least empty string
        "explanation": bank_question.get("explanation"),
        "marks": bank_question.get("marks"),
        "hardness_level": bank_question.get("hardness_level"),
        # We keep the original type (MCQ, etc)
        "question_type": bank_question.get("question_type"),
        # "question_type": "SOLVED_EXAMPLE" if ... else "EXERCISE"
        # Logic discussed: keep original type or use new Enum?
        # User requested: "the question will still have the type mcq or msq
        # etc. after this using the bank_question table's type attribute,
        # but I will add two more field in db to the gen_questions table
        # is_solved_example and is_exercise_question"
        # Options for MCQ/MSQ
        "option1": bank_question.get("option1"),
        "option2": bank_question.get("option2"),
        "option3": bank_question.get("option3"),
        "option4": bank_question.get("option4"),
        # Answers
        "correct_mcq_option": bank_question.get("correct_mcq_option"),
        "msq_option1_answer": bank_question.get("msq_option1_answer"),
        "msq_option2_answer": bank_question.get("msq_option2_answer"),
        "msq_option3_answer": bank_question.get("msq_option3_answer"),
        "msq_option4_answer": bank_question.get("msq_option4_answer"),
        # Flags (The new columns)
        "is_solved_example": (
            True if request_type == QuestionRequestType.SOLVED_EXAMPLE else False
        ),
        "is_exercise_question": (
            True if request_type == QuestionRequestType.EXERCISE_QUESTION else False
        ),
        # Other fields
        "match_the_following_columns": bank_question.get(
            "match_columns"
        ),  # Note column mismatch handling
        # svgs might handle differently if they are not in gen_questions
        # directly but in gen_images
        # We will handle SVGs separately if needed, but bank_questions
        # has 'svgs' string column maybe?
        "svgs": [],
        # bank_questions has 'svgs' text column. gen_questions doesn't
        # typically store it directly in column?
        # Wait, service.py handles 'svgs' list by popping it.
        # bank_questions schema: svgs text null.
        # If bank_questions stores it as string, we might need to parse it
        # if service expects a list of objects.
        # But let's look at service.py: it pops "svgs" list.
    }

    # Handle SVGs
    # bank_questions 'svgs' is text (likely stringified JSON or just string).
    # If it's a list of strings/objects, we should parse it.
    raw_svgs = bank_question.get("svgs")
    if raw_svgs:
        # Assuming simple string for now, or we wrap it in the expected list format
        # If the service expects a list of dicts/objects:
        payload["svgs"] = [{"svg": raw_svgs}]

    return payload


def fetch_questions_from_bank(
    supabase_client: supabase.Client,
    concept_names: list[str],
    concepts_name_to_id: dict[str, str],
    count: int,
    difficulty: str,
    request_type: QuestionRequestType,
) -> list[dict[str, Any]]:
    """
    Fetches questions from bank_questions table.
    1. Filter by is_solved_example/is_from_exercise base on request_type.
    2. Filter by concept_ids (derived from concept_names).
    3. Filter by difficulty.
    4. If not enough questions, relax difficulty.
    5. Return list of question payloads ready for insertion.
    """

    # correct flag column
    flag_filter = (
        "is_solved_example"
        if request_type == QuestionRequestType.SOLVED_EXAMPLE
        else "is_from_exercise"
    )

    # Get concept IDs
    concept_ids = [concepts_name_to_id.get(c) for c in concept_names if concepts_name_to_id.get(c)]

    if not concept_ids:
        logger.warning(f"No valid concept IDs found for names: {concept_names}")
        return []

    # Helper to run query
    def run_query(target_diff: str | None = None):
        # We need to join with bank_questions_concepts_maps to filter by concept
        # Supabase-py doesn't support complex joins easily for filtering
        # in one go without raw sql or views usually, but we can try
        # filtering on the foreign key if set up, or use the mapping table.

        # Strategy: Get valid bank_question_ids from mapping table first for these concepts
        # Then fetch questions.

        # 1. Get bank_question_ids for these concepts
        map_query = (
            supabase_client.table("bank_questions_concepts_maps")
            .select("bank_question_id")
            .in_("concept_id", concept_ids)
        )

        map_res = map_query.execute()
        valid_q_ids = [row["bank_question_id"] for row in map_res.data]

        if not valid_q_ids:
            logger.info("No questions were found for the request in the bank")
            return []
        else:
            logger.info(f"Number of quesitons found in bank for the req are : {len(valid_q_ids)}")

        # 2. Fetch questions
        query = (
            supabase_client.table("bank_questions")
            .select("*, bank_questions_concepts_maps(concept_id)")
            .in_("id", valid_q_ids)
            .eq(flag_filter, True)
        )

        # Filter out questions with is_image_needed=True if USE_IMAGE_NEEDED is False
        if not USE_IMAGE_NEEDED:
            query = query.eq("is_image_needed", False)

        # Filter out questions with is_incomplete=True if USE_INCOMPLETE is False
        if not USE_INCOMPLETE:
            query = query.eq("is_incomplete", False)

        if target_diff:
            query = query.eq("hardness_level", target_diff)

        res = query.execute()
        logger.info(f"Number of questions found after running the fetching query : {len(res.data)}")
        return res.data

    # Attempt 1: Strict difficulty
    questions = run_query(difficulty)

    # Attempt 2: Relax difficulty if needed
    if len(questions) < count:
        logger.info(
            f"Not enough {request_type.value} questions with difficulty "
            f"{difficulty}. Found {len(questions)}. Relaxing difficulty."
        )
        more_questions = run_query(None)  # Fetch all for these concepts + flag
        logger.info(f"Number of the more_questions is : {len(more_questions)}")
        # Exclude ones we already have
        existing_ids = {q["id"] for q in questions}
        additional = [q for q in more_questions if q["id"] not in existing_ids]

        questions.extend(additional)

    # Shuffle and pick count
    if len(questions) > count:
        questions = random.sample(questions, count)
    logger.info(f"Number of questions selected from bank  : {len(questions)}")
    # Format for downstream
    formatted_questions = []

    for q in questions:
        # We need to preserve concept_ids for the insertion logic
        # which uses 'concept_ids' key.
        # q['bank_questions_concepts_maps'] will be a list of dicts like
        # [{'concept_id': ...}, ...] due to select above
        q_concept_ids = [m["concept_id"] for m in q.get("bank_questions_concepts_maps", [])]

        # If join didn't return it (depends on RLS/relationships),
        # use the batch concepts as fallback
        if not q_concept_ids:
            q_concept_ids = concept_ids

        payload = extract_bank_question_to_gen_payload(q, request_type)

        formatted_questions.append(
            {
                "question": payload,
                "concept_ids": q_concept_ids,  # This is required by insert_batch_to_supabase
            }
        )

    return formatted_questions

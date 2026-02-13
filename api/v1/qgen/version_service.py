"""
Question Version Service

Handles version management for gen_questions, enabling undo/redo functionality.
"""

import logging
from typing import Any

import supabase

logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURABLE VERSION FIELDS
# These are the fields that get versioned. Easy to modify this list.
# ============================================================================

VERSION_FIELDS = [
    "question_text",
    "answer_text",
    "explanation",
    "option1",
    "option2",
    "option3",
    "option4",
    "correct_mcq_option",
    "msq_option1_answer",
    "msq_option2_answer",
    "msq_option3_answer",
    "msq_option4_answer",
    "question_type",
    "hardness_level",
    "marks",
    "match_the_following_columns",
]


def extract_version_data(question_data: dict[str, Any]) -> dict[str, Any]:
    """Extract only the versioned fields from question data."""
    return {key: question_data.get(key) for key in VERSION_FIELDS if key in question_data}


def create_initial_version(
    supabase_client: supabase.Client,
    gen_question_id: str,
    question_data: dict[str, Any],
) -> dict[str, Any] | None:
    """
    Create version 0 when a question is first created.

    Args:
        supabase_client: Supabase client instance
        gen_question_id: The ID of the newly created question
        question_data: The question data (all fields)

    Returns:
        The created version record, or None if failed
    """
    try:
        version_data = extract_version_data(question_data)
        version_data.update(
            {
                "gen_question_id": gen_question_id,
                "version_index": 0,
                "is_active": True,
                "is_deleted": False,
            }
        )

        result = supabase_client.table("gen_question_versions").insert(version_data).execute()

        if result.data:
            logger.debug(f"Created initial version (v0) for question {gen_question_id}")
            return result.data[0]

        return None

    except Exception as e:
        logger.error(f"Failed to create initial version for question {gen_question_id}: {e}")
        return None


def create_new_version_on_update(
    supabase_client: supabase.Client,
    gen_question_id: str,
    new_question_data: dict[str, Any],
) -> dict[str, Any] | None:
    """
    Create a new version when a question is updated.

    This function:
    1. Fetches the current question to get all fields
    2. Merges with the update data
    3. Gets the current active version index
    4. Marks all versions with index > current as is_deleted=true
    5. Sets current active version to is_active=false
    6. Creates new version with index = max + 1, is_active=true

    Args:
        supabase_client: Supabase client instance
        gen_question_id: The ID of the question being updated
        new_question_data: The update data (may be partial)

    Returns:
        The created version record, or None if failed
    """
    try:
        # 0. Fetch the current question to get ALL fields (required for NOT NULL constraints)
        current_question_result = (
            supabase_client.table("gen_questions").select("*").eq("id", gen_question_id).single().execute()
        )

        if not current_question_result.data:
            logger.error(f"Question {gen_question_id} not found, cannot create version")
            return None

        # Merge current question data with the updates (updates take precedence)
        full_question_data = {**current_question_result.data, **new_question_data}

        # 1. Get current active version
        active_result = (
            supabase_client.table("gen_question_versions")
            .select("id, version_index")
            .eq("gen_question_id", gen_question_id)
            .eq("is_active", True)
            .eq("is_deleted", False)
            .single()
            .execute()
        )

        if not active_result.data:
            # No active version exists - create initial version first
            logger.warning(f"No active version found for question {gen_question_id}, creating initial version")
            return create_initial_version(supabase_client, gen_question_id, full_question_data)

        current_active = active_result.data
        current_index = current_active["version_index"]

        # 2. Mark all versions with index > current as deleted (invalidate redo history)
        (
            supabase_client.table("gen_question_versions")
            .update({"is_deleted": True})
            .eq("gen_question_id", gen_question_id)
            .gt("version_index", current_index)
            .eq("is_deleted", False)
            .execute()
        )

        # 3. Set current active to inactive
        (
            supabase_client.table("gen_question_versions")
            .update({"is_active": False})
            .eq("id", current_active["id"])
            .execute()
        )

        # 4. Get max version index for this question
        max_result = (
            supabase_client.table("gen_question_versions")
            .select("version_index")
            .eq("gen_question_id", gen_question_id)
            .order("version_index", desc=True)
            .limit(1)
            .execute()
        )

        max_index = max_result.data[0]["version_index"] if max_result.data else -1
        new_index = max_index + 1

        # 5. Create new version with FULL question data (merged)
        version_data = extract_version_data(full_question_data)
        version_data.update(
            {
                "gen_question_id": gen_question_id,
                "version_index": new_index,
                "is_active": True,
                "is_deleted": False,
            }
        )

        result = supabase_client.table("gen_question_versions").insert(version_data).execute()

        if result.data:
            logger.debug(f"Created new version (v{new_index}) for question {gen_question_id}")
            return result.data[0]

        return None

    except Exception as e:
        logger.error(f"Failed to create new version for question {gen_question_id}: {e}")
        return None

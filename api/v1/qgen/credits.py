"""
Credits management logic for QGen.
"""

import logging
import uuid

from api.v1.auth import get_supabase_client

logger = logging.getLogger(__name__)


def check_user_has_credits(user_id: uuid.UUID) -> bool:
    """
    Checks if the user has at least 1 credit.

    Args:
        user_id: The UUID of the user.

    Returns:
        True if user has credits > 0, False otherwise.
    """
    try:
        supabase = get_supabase_client()
        response = supabase.table("users").select("credits").eq("id", str(user_id)).single().execute()

        if not response.data:
            logger.warning(f"User {user_id} not found when checking credits.")
            return False

        current_credits = response.data.get("credits", 0)
        return current_credits > 0

    except Exception as e:
        logger.error(f"Error checking credits for user {user_id}: {e}")
        # Fail safe to False to prevent abuse if DB is down
        return False


def deduct_user_credits(user_id: uuid.UUID, credits_used: int) -> None:
    """
    Deducts credits from the user's account safely (floor at 0).
    Expected to be called AFTER a successful request.

    Args:
        user_id: The UUID of the user.
        credits_used: Amount of credits to deduct.
    """
    if credits_used <= 0:
        return

    try:
        supabase = get_supabase_client()

        # 1. Fetch current credits
        response = supabase.table("users").select("credits").eq("id", str(user_id)).single().execute()

        if not response.data:
            logger.error(f"User {user_id} not found when deducting credits.")
            return

        current_credits = response.data.get("credits", 0)

        # 2. Calculate new credits (floor at 0)
        new_credits = max(0, current_credits - credits_used)

        # 3. Update credits
        supabase.table("users").update({"credits": new_credits}).eq("id", str(user_id)).execute()

        logger.info(f"Deducted {credits_used} credits from user {user_id}. Old: {current_credits}, New: {new_credits}")

    except Exception as e:
        logger.error(f"Error deducting credits for user {user_id}: {e}")
        # Note: In a production environment with strict billing, we might want to
        # raise this exception or have a retry mechanism.
        # For now, we log it as per standard practice where post-action deduction failure
        # shouldn't crash the already-successful user response if possible,
        # but alerting is needed.

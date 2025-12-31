"""
Module To Implement General Security Routes
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from supabase import Client

from api.v1.auth import get_supabase_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/security", tags=["security"])


class CheckPhoneRequest(BaseModel):
    """
    phone: str
    """

    phone: str


class CheckPhoneResponse(BaseModel):
    """
    exists: bool
    """

    exists: bool


@router.post("/check_phone_number", response_model=CheckPhoneResponse)
def check_phone_number(
    request: CheckPhoneRequest,
    supabase: Client = Depends(get_supabase_client),
):
    """
    Checks if a user with the given phone number exists in the public.users table.
    This endpoint is open and does not require authentication.
    """
    try:
        # We select only the phone_num to verify existence
        logger.debug(request.phone)
        response = (
            supabase.table("users")
            .select("phone_num")
            .eq("phone_num", request.phone)
            .execute()
        )

        exists = len(response.data) > 0 if response.data else False

        return CheckPhoneResponse(exists=exists)

    except Exception as e:
        logger.error("Error checking phone number: %s", e)
        # In case of error, we can return False or raise an exception.
        # Returning False might be safer to avoid leaking error details,
        # but 500 is appropriate for server errors.
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error checking phone number",
        ) from e

"""
API v1 router with authentication dependency and a sample endpoint.
"""

import logging

from fastapi import APIRouter, Depends, Request

from .auth import require_supabase_user
from .qgen.router import router as qgen_router

logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/api/v1",
    dependencies=[Depends(require_supabase_user)],
)

router.include_router(qgen_router)


@router.get("/hello")
def hello(request: Request) -> dict:
    """
    A sample endpoint that requires authentication.
    """
    user = getattr(request.state, "supabase_user", None)
    user_id = getattr(user, "id", None) if user is not None else None
    email = getattr(user, "email", None) if user is not None else None

    if isinstance(user, dict):
        user_id = user_id or user.get("id")
        email = email or user.get("email")

    return {
        "message": "hello",
        "authenticated": True,
        "user": {"id": user_id, "email": email},
    }

"""
API v1 router with authentication dependency and a sample endpoint.
"""

import logging

from fastapi import APIRouter, Depends, Request

from .auth import require_supabase_user
from .auth_exchange import router as auth_exchange_router
from .bank.router import router as bank_router
from .qgen.router import router as qgen_router
from .security import router as security_router
from .sms_hook import router as sms_hook_router

logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/api/v1",
    # dependencies=[Depends(require_supabase_user)], # Removed global dependency
)

router.include_router(qgen_router, dependencies=[Depends(require_supabase_user)])
router.include_router(security_router)
router.include_router(sms_hook_router)
router.include_router(auth_exchange_router)
router.include_router(bank_router)


@router.get("/hello", dependencies=[Depends(require_supabase_user)])
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

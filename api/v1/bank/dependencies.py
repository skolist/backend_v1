import logging
from fastapi import Depends, HTTPException, status
from supabase import Client
from api.v1.auth import require_supabase_user, get_supabase_client

logger = logging.getLogger(__name__)

def require_admin(
    user: dict = Depends(require_supabase_user),
    supabase_client: Client = Depends(get_supabase_client)
) -> dict:
    """
    Dependency that enforces admin access by checking 'user_type' in public.users table.
    """
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    user_id = user.get("id") if isinstance(user, dict) else getattr(user, "id", None)
    
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User ID not found"
        )

    try:
        # Query public.users table for user_type
        response = supabase_client.table("users").select("user_type").eq("id", user_id).single().execute()
        
        if not response.data:
             raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User profile not found"
            )
            
        user_type = response.data.get("user_type")
        
        if user_type != "skolist-admin":
            logger.warning(f"Unauthorized access attempt by user {user_id} with type {user_type}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )
            
        return user

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validating admin status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error validating permissions"
        )

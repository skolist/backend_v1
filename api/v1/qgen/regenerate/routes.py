"""
Regenerate question API routes.
"""

import logging

import supabase
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response

from api.v1.auth import get_supabase_client, require_supabase_user
from api.v1.qgen.credits import check_user_has_credits, deduct_user_credits
from api.v1.qgen.regenerate.service import QuestionProcessingError, RegenerateService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/regenerate_question")
async def regenerate_question(
    gen_question_id: str,
    supabase_client: supabase.Client = Depends(get_supabase_client),
    user: dict = Depends(require_supabase_user),
):
    """
    API endpoint to regenerate a new question on same concept.
    """
    user_id = user.id

    # Check credits
    if not check_user_has_credits(user_id):
        return Response(status_code=status.HTTP_402_PAYMENT_REQUIRED, content="Insufficient credits")

    logger.info(
        "Received regenerate request",
        extra={"gen_question_id": gen_question_id, "user_id": user_id},
    )

    try:
        # Fetch Question
        gen_question = supabase_client.table("gen_questions").select("*").eq("id", gen_question_id).execute()

        if not gen_question.data:
            raise HTTPException(status_code=404, detail="Gen Question not found")

        gen_question_data = gen_question.data[0]

        # Fetch existing SVGs for this question
        gen_images = (
            supabase_client.table("gen_images")
            .select("*")
            .eq("gen_question_id", gen_question_id)
            .order("position")
            .execute()
        )

        # Add SVGs to gen_question_data
        if gen_images.data:
            logger.debug(
                "Received svgs for the question for regeneration",
                extra={"gen_images": gen_images.data, "user_id": user_id},
            )
            gen_question_data["svgs"] = [{"svg": img["svg_string"]} for img in gen_images.data if img.get("svg_string")]
        else:
            logger.debug(
                "No SVGS were found for this question for regeneration",
                extra={"gen_question_id": gen_question_id, "user_id": user_id},
            )

        # Process
        await RegenerateService.regenerate_question(
            gen_question_data=gen_question_data,
            gen_question_id=gen_question_id,
            supabase_client=supabase_client,
        )

        # Deduct credits
        deduct_user_credits(user_id, 2)

        logger.info(
            "Regenerate completed successfully",
            extra={"gen_question_id": gen_question_id},
        )

        return Response(status_code=status.HTTP_200_OK)

    except HTTPException:
        raise
    except QuestionProcessingError as e:
        logger.exception("Error regenerating question")
        raise HTTPException(status_code=500, detail="Internal Server Error") from e
    except Exception as e:
        logger.exception("Unexpected error regenerating question")
        raise HTTPException(status_code=500, detail="Internal Server Error") from e

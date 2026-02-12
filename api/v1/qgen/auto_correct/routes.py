import logging

import supabase
from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import Response

from api.v1.auth import get_supabase_client, require_supabase_user
from api.v1.qgen.auto_correct.service import AutoCorrectService, QuestionProcessingError
from api.v1.qgen.credits import check_user_has_credits, deduct_user_credits

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/auto_correct_question")
async def auto_correct_question(
    request: Request,
    gen_question_id: str = Form(..., description="UUID of the question to correct"),
    supabase_client: supabase.Client = Depends(get_supabase_client),
    user: dict = Depends(require_supabase_user),
):
    """
    API endpoint to auto-correct a question using backend-generated screenshot.
    """
    user_id = user.id

    # Check credits
    if not check_user_has_credits(user_id):
        return Response(
            status_code=status.HTTP_402_PAYMENT_REQUIRED, content="Insufficient credits"
        )

    logger.info(
        "Received auto-correct request",
        extra={"gen_question_id": gen_question_id, "user_id": user_id},
    )

    try:
        # Fetch Question
        gen_question = (
            supabase_client.table("gen_questions").select("*").eq("id", gen_question_id).execute()
        )

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
            gen_question_data["svgs"] = [
                {"svg": img["svg_string"]} for img in gen_images.data if img.get("svg_string")
            ]
        else:
            logger.debug(
                "No SVGS were found for this question for regeneration",
                extra={"gen_question_id": gen_question_id, "user_id": user_id},
            )

        # Get browser service from app state
        browser_service = getattr(request.app.state, "browser_service", None)
        if not browser_service:
            raise HTTPException(status_code=503, detail="Browser service unavailable")

        # Process
        await AutoCorrectService.correct_question(
            gen_question_data=gen_question_data,
            gen_question_id=gen_question_id,
            supabase_client=supabase_client,
            browser_service=browser_service,
        )

        # Deduct credits
        deduct_user_credits(user_id, 2)

        return Response(status_code=status.HTTP_200_OK)

    except HTTPException:
        # Re-raise HTTP exceptions (404, 402, 503, etc.) as-is
        raise
    except QuestionProcessingError as e:
        logger.exception("Error auto correcting question")
        raise HTTPException(status_code=500, detail="Internal Server Error") from e
    except Exception as e:
        logger.exception("Unexpected error auto correcting question")
        raise HTTPException(status_code=500, detail="Internal Server Error") from e

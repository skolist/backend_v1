import logging
import os

import supabase
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import Response
from google import genai

from api.v1.auth import get_supabase_client, require_supabase_user
from api.v1.qgen.credits import check_user_has_credits, deduct_user_credits
from api.v1.qgen.regenerate_with_prompt.service import (
    QuestionProcessingError,
    RegenerateWithPromptService,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/regenerate_question_with_prompt")
async def regenerate_question_with_prompt(
    request: Request,
    gen_question_id: str = Form(..., description="UUID of the question to regenerate"),
    prompt: str | None = Form(None, description="Custom prompt for regeneration"),
    is_camera_capture: bool = Form(
        False, description="Flag indicating if this is from camera capture"
    ),
    files: list[UploadFile] = File(default=[], description="Optional files to attach"),
    supabase_client: supabase.Client = Depends(get_supabase_client),
    user: dict = Depends(require_supabase_user),
):
    """
    API endpoint to regenerate a question with a custom prompt, files,
    and auto-generated screenshot.
    """
    user_id = user.id

    if not check_user_has_credits(user_id):
        return Response(
            status_code=status.HTTP_402_PAYMENT_REQUIRED, content="Insufficient credits"
        )

    logger.info(
        "Received regenerate with prompt request",
        extra={
            "gen_question_id": gen_question_id,
            "has_custom_prompt": bool(prompt),
            "is_camera_capture": is_camera_capture,
            "file_count": len(files),
            "user_id": user_id,
        },
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

        # Get browser service
        browser_service = getattr(request.app.state, "browser_service", None)
        if not browser_service:
            raise HTTPException(status_code=503, detail="Browser service unavailable")

        # Initialize Gemini Client
        gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

        # Process
        await RegenerateWithPromptService.regenerate_question(
            gen_question_data=gen_question_data,
            gen_question_id=gen_question_id,
            supabase_client=supabase_client,
            browser_service=browser_service,
            gemini_client=gemini_client,
            custom_prompt=prompt,
            files=files,
            is_camera_capture=is_camera_capture,
        )

        deduct_user_credits(user_id, 2)

        return Response(status_code=status.HTTP_200_OK)

    except HTTPException:
        raise
    except QuestionProcessingError as e:
        logger.exception("Error processing regeneration")
        raise HTTPException(status_code=500, detail="Internal Server Error") from e
    except Exception as e:
        logger.exception("Unexpected error in generation")
        raise HTTPException(status_code=500, detail="Internal Server Error") from e

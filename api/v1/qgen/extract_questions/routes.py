"""
Routes for the extract_questions endpoint.
"""

import logging

import supabase
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse

from api.v1.auth import get_supabase_client, require_supabase_user
from api.v1.qgen.credits import check_user_has_credits, deduct_user_credits
from api.v1.qgen.extract_questions.service import (
    ExtractionProcessingError,
    ExtractionValidationError,
    ExtractQuestionsService,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/extract_questions")
async def extract_questions(
    file: UploadFile = File(..., description="Image or PDF file containing questions"),
    activity_id: str = Form(..., description="UUID of the activity"),
    qgen_draft_id: str = Form(..., description="UUID of the draft to add section to"),
    prompt: str | None = Form(None, description="Optional custom instructions for extraction"),
    section_name: str | None = Form(None, description="Optional name for the new section"),
    supabase_client: supabase.Client = Depends(get_supabase_client),
    user: dict = Depends(require_supabase_user),
):
    """
    API endpoint to extract questions from an uploaded file (image/PDF).

    Creates a new section in the draft and inserts extracted questions into it.

    Returns:
        JSON with section_id, section_name, questions_extracted count, and question IDs
    """
    user_id = user.id

    # Check credits
    if not check_user_has_credits(user_id):
        return JSONResponse(
            status_code=status.HTTP_402_PAYMENT_REQUIRED, content={"error": "Insufficient credits"}
        )

    logger.info(
        "Received extract_questions request",
        extra={
            "user_id": user_id,
            "activity_id": activity_id,
            "qgen_draft_id": qgen_draft_id,
            "file_name": file.filename,
        },
    )

    try:
        # Validate that activity exists and belongs to user
        activity = (
            supabase_client.table("activities")
            .select("id, user_id")
            .eq("id", activity_id)
            .execute()
        )

        if not activity.data:
            raise HTTPException(status_code=404, detail="Activity not found")

        if activity.data[0].get("user_id") != user_id:
            raise HTTPException(status_code=403, detail="Access denied to this activity")

        # Validate that draft exists
        draft = supabase_client.table("qgen_drafts").select("id").eq("id", qgen_draft_id).execute()

        if not draft.data:
            raise HTTPException(status_code=404, detail="Draft not found")

        # Process extraction
        result = await ExtractQuestionsService.extract_and_insert(
            file=file,
            activity_id=activity_id,
            qgen_draft_id=qgen_draft_id,
            supabase_client=supabase_client,
            section_name=section_name,
            custom_prompt=prompt,
        )

        # Deduct credits based on questions extracted (min 3 credits)
        questions_count = result.get("questions_extracted", 0)
        credits_to_deduct = max(3, questions_count)
        deduct_user_credits(user_id, credits_to_deduct)

        logger.info(
            "Extract questions completed",
            extra={
                "user_id": user_id,
                "section_id": result.get("section_id"),
                "questions_extracted": questions_count,
                "credits_deducted": credits_to_deduct,
            },
        )

        return JSONResponse(status_code=status.HTTP_201_CREATED, content=result)

    except ExtractionValidationError as e:
        logger.warning(f"Validation error in extract_questions: {e}")
        raise HTTPException(status_code=400, detail=str(e)) from e

    except ExtractionProcessingError:
        logger.exception("Error extracting questions")
        raise HTTPException(
            status_code=500, detail="Failed to extract questions from file"
        ) from None

    except HTTPException:
        raise

    except Exception:
        logger.exception("Unexpected error in extract_questions")
        raise HTTPException(status_code=500, detail="Internal Server Error") from None

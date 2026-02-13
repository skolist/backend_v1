import logging

import supabase
from fastapi import Depends, Form, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from api.v1.auth import get_supabase_client, require_supabase_user
from api.v1.qgen.credits import check_user_has_credits, deduct_user_credits
from api.v1.qgen.edit_svg.service import EditSVGService, SVGEditError

logger = logging.getLogger(__name__)


class EditSVGResponse(BaseModel):
    id: str
    svg_string: str
    gen_question_id: str
    position: int | None


async def edit_svg(
    gen_image_id: str = Form(..., description="UUID of the image to edit"),
    instruction: str = Form(..., description="Natural language instruction for editing the SVG"),
    supabase_client: supabase.Client = Depends(get_supabase_client),
    user: dict = Depends(require_supabase_user),
):
    """
    API endpoint to edit an SVG using natural language instruction.

    The AI will interpret the instruction and modify the SVG accordingly.
    Examples of instructions:
    - "Move the label 'r = 10 cm' to the left"
    - "Change theta to 45 degrees"
    - "Make the circle bigger"
    - "Add a label 'O' at the center"
    """
    user_id = user.id

    # Check credits
    if not check_user_has_credits(user_id):
        return JSONResponse(status_code=status.HTTP_402_PAYMENT_REQUIRED, content={"error": "Insufficient credits"})

    logger.info(
        "Received edit SVG request",
        extra={"gen_image_id": gen_image_id, "instruction": instruction, "user_id": user_id},
    )

    try:
        # Process the edit
        result = await EditSVGService.edit_svg(
            gen_image_id=gen_image_id,
            instruction=instruction,
            supabase_client=supabase_client,
        )

        # Deduct credits (1 credit for SVG edit, less than question generation)
        deduct_user_credits(user_id, 1)

        return JSONResponse(status_code=status.HTTP_200_OK, content=result)

    except SVGEditError as e:
        logger.error(f"SVG edit error: {e}")
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.exception("Unexpected error editing SVG")
        raise HTTPException(status_code=500, detail="Internal Server Error") from e

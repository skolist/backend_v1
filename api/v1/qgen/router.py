# pylint: disable=cell-var-from-loop
# pylint: disable=broad-exception-caught
# pylint: disable=too-many-locals
"""
Router for the dummy endpoint
"""
import logging
from fastapi import APIRouter, status

from .question_generator import generate_questions
from .auto_correct_question import auto_correct_question
from .regenerate_question import regenerate_question
from .regenerate_question_with_prompt import regenerate_question_with_prompt

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/qgen", tags=["qgen"])

router.post("/generate_questions", status_code=status.HTTP_201_CREATED)(
    generate_questions
)
router.post("/auto_correct_question", status_code=status.HTTP_200_OK)(
    auto_correct_question
)
router.post("/regenerate_question", status_code=status.HTTP_200_OK)(
    regenerate_question
)
router.post("/regenerate_question_with_prompt", status_code=status.HTTP_200_OK)(
    regenerate_question_with_prompt
)
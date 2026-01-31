# pylint: disable=cell-var-from-loop
# pylint: disable=broad-exception-caught
# pylint: disable=too-many-locals
"""
Router for the dummy endpoint
"""
import logging
from fastapi import APIRouter, status

from .generate_questions.routes import generate_questions
from .auto_correct.routes import auto_correct_question
from .regenerate.routes import regenerate_question
from .regenerate_with_prompt.routes import regenerate_question_with_prompt
from .extract_questions.routes import extract_questions
from .edit_svg.routes import edit_svg
from .get_feedback import get_feedback
from .download_pdf import download_pdf
from .download_docx import download_docx


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/qgen", tags=["qgen"])

router.post("/generate_questions", status_code=status.HTTP_201_CREATED)(generate_questions)
router.post("/auto_correct_question", status_code=status.HTTP_200_OK)(auto_correct_question)
router.post("/regenerate_question", status_code=status.HTTP_200_OK)(regenerate_question)
router.post("/regenerate_question_with_prompt", status_code=status.HTTP_200_OK)(regenerate_question_with_prompt)
router.post("/extract_questions", status_code=status.HTTP_201_CREATED)(extract_questions)
router.post("/edit_svg", status_code=status.HTTP_200_OK)(edit_svg)
router.post("/get_feedback", status_code=status.HTTP_200_OK)(get_feedback)
router.post("/download_pdf", status_code=status.HTTP_200_OK)(download_pdf)
router.post("/download_docx", status_code=status.HTTP_200_OK)(download_docx)



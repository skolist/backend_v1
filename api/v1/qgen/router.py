# pylint: disable=cell-var-from-loop
# pylint: disable=broad-exception-caught
# pylint: disable=too-many-locals
"""
Router for the dummy endpoint
"""

import logging
import uuid
from typing import List, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from supabase import Client

from api.v1.auth import get_supabase_client

from api.v1.qgen import mocker

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/generate", tags=["generation"])


class QuestionTypeConfig(BaseModel):
    """
    Question Type Configuration
    """

    type: Literal[
        "MCQ", "SHORT_ANSWER", "LONG_ANSWER", "TRUE_FALSE", "FILL_IN_THE_BLANK", "MSQ"
    ]
    count: int


class DifficultyDistribution(BaseModel):
    """
    Difficulty Distribution Configuration
    """

    easy: int = Field(..., ge=0, le=100)
    medium: int = Field(..., ge=0, le=100)
    hard: int = Field(..., ge=0, le=100)


class QuestionConfig(BaseModel):
    """
    Question Configuration
    """

    question_types: List[QuestionTypeConfig]
    difficulty_distribution: DifficultyDistribution


class GenerateQuestionsRequest(BaseModel):
    """
    Generate Questions Request
    """

    activity_id: uuid.UUID
    concept_ids: List[uuid.UUID]
    config: QuestionConfig


class GenerateQuestionsResponse(BaseModel):
    """
    Generate Questions Response
    """

    success: bool
    message: str
    data: dict


@router.post("/questions", response_model=GenerateQuestionsResponse)
def generate_questions(
    request: GenerateQuestionsRequest,
    supabase: Client = Depends(get_supabase_client),
):
    """
    Dummy route
    """
    generated_count = 0

    # Map question types to mocker functions
    type_map = {
        "MCQ": mocker.generate_mcq,
        "SHORT_ANSWER": mocker.generate_short_answer,
        "LONG_ANSWER": mocker.generate_long_answer,
        "TRUE_FALSE": mocker.generate_true_false,
        "FILL_IN_THE_BLANK": mocker.generate_fill_in_the_blank,
        "MSQ": mocker.generate_msq,
    }

    db_type_map = {
        "MCQ": "mcq",
        "SHORT_ANSWER": "short_answer",
        "LONG_ANSWER": "long_answer",
        "TRUE_FALSE": "true_or_false",
        "FILL_IN_THE_BLANK": "fill_in_the_blanks",
        "MSQ": "msq",
    }

    for q_type_config in request.config.question_types:
        q_type = q_type_config.type
        count = q_type_config.count

        if q_type not in type_map:
            logger.warning("Unsupported question type requested: %s", q_type)
            continue

        generator_func = type_map[q_type]
        db_question_type = db_type_map.get(q_type, "short_answer")

        for _ in range(count):
            try:
                question_obj = generator_func(
                    # activity_id=request.activity_id,
                    # concept_ids=request.concept_ids,
                    # difficulty=request.config.difficulty_distribution,
                )

                # Convert Pydantic model to dict
                q_data = question_obj.model_dump()

                # Prepare Options JSONB
                options_list = []

                # Handle Answer extraction first to determine correctness for options
                answer_val = q_data.get("answer")
                answers_list = q_data.get("answers")  # For MSQ

                gen_answer_str = None
                if answer_val is not None:
                    gen_answer_str = str(answer_val)
                elif answers_list is not None:
                    gen_answer_str = str(answers_list)

                # Helper to check correctness
                def is_correct(idx: int, txt: str) -> bool:
                    # answer_val can be int (index) or str (text) or bool
                    if isinstance(answer_val, int):
                        return answer_val == idx
                    if isinstance(answer_val, str):
                        return answer_val == txt
                    if answers_list:
                        return idx in answers_list
                    return False

                # Convert flat options to structured list
                if "option1" in q_data:
                    options_list.append(
                        {
                            "id": "opt-1",
                            "text": q_data["option1"],
                            "isCorrect": is_correct(1, q_data["option1"]),
                        }
                    )
                if "option2" in q_data:
                    options_list.append(
                        {
                            "id": "opt-2",
                            "text": q_data["option2"],
                            "isCorrect": is_correct(2, q_data["option2"]),
                        }
                    )
                if "option3" in q_data:
                    options_list.append(
                        {
                            "id": "opt-3",
                            "text": q_data["option3"],
                            "isCorrect": is_correct(3, q_data["option3"]),
                        }
                    )
                if "option4" in q_data:
                    options_list.append(
                        {
                            "id": "opt-4",
                            "text": q_data["option4"],
                            "isCorrect": is_correct(4, q_data["option4"]),
                        }
                    )

                insert_data = {
                    "activity_id": str(request.activity_id),
                    "options": options_list,  # JSONB
                    "question_type": db_question_type,
                    "gen_question_text": q_data.get("question"),
                    "explanation": q_data.get("explanation"),
                    "gen_answer": gen_answer_str,
                    "hardness": "medium",  # Default/Mock
                    "marks": 1,  # Default/Mock
                    "is_in_draft": False,
                }

                # Insert into gen_questions
                res = supabase.table("gen_questions").insert(insert_data).execute()

                if res.data and len(res.data) > 0:
                    new_question_id = res.data[0]["id"]

                    # Insert into gen_questions_concepts_maps
                    if request.concept_ids:
                        map_inserts = [
                            {"gen_question_id": new_question_id, "concept_id": str(cid)}
                            for cid in request.concept_ids
                        ]
                        supabase.table("gen_questions_concepts_maps").insert(
                            map_inserts
                        ).execute()

                    generated_count += 1

            except Exception as e:
                logger.error(
                    "Error generating/storing question of type %s: %s", q_type, e
                )

    return GenerateQuestionsResponse(
        success=True,
        message=f"Successfully generated and stored {generated_count} questions.",
        data={},
    )

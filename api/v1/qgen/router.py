import logging
import uuid
from typing import List, Literal

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from supabase import Client

from api.v1.auth import get_supabase_client
from ai.schemas.questions import (
    MCQ4,
    MSQ4,
    FillInTheBlank,
    LongAnswer,
    ShortAnswer,
    TrueFalse,
)
from api.v1.qgen import mocker

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/generate", tags=["generation"])


class QuestionTypeConfig(BaseModel):
    type: Literal[
        "MCQ", "SHORT_ANSWER", "LONG_ANSWER", "TRUE_FALSE", "FILL_IN_THE_BLANK", "MSQ"
    ]
    count: int


class DifficultyDistribution(BaseModel):
    easy: int = Field(..., ge=0, le=100)
    medium: int = Field(..., ge=0, le=100)
    hard: int = Field(..., ge=0, le=100)


class QuestionConfig(BaseModel):
    question_types: List[QuestionTypeConfig]
    difficulty_distribution: DifficultyDistribution


class GenerateQuestionsRequest(BaseModel):
    activity_id: uuid.UUID
    concept_ids: List[uuid.UUID]
    config: QuestionConfig


class GenerateQuestionsResponse(BaseModel):
    success: bool
    message: str
    data: dict


@router.post("/questions", response_model=GenerateQuestionsResponse)
def generate_questions(
    request: GenerateQuestionsRequest,
    supabase: Client = Depends(get_supabase_client),
):
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

    for q_type_config in request.config.question_types:
        q_type = q_type_config.type
        count = q_type_config.count
        
        if q_type not in type_map:
            logger.warning(f"Unsupported question type requested: {q_type}")
            continue
            
        generator_func = type_map[q_type]
        
        for _ in range(count):
            try:
                question_obj = generator_func(
                    activity_id=request.activity_id,
                    concept_ids=request.concept_ids,
                    difficulty=request.config.difficulty_distribution
                )
                
                # Convert Pydantic model to dict for JSONB storage
                q_data = question_obj.model_dump()
                q_data["type"] = q_type # Ensure type is part of the content if needed, though usually inferred or separate. 
                # The schema says "question type, question and the answer" in gen_content description.
                
                # Prepare insert data for gen_questions
                # marks and hardness are hardcoded for now as per previous logic/mock
                insert_data = {
                    "gen_content": q_data,
                    "activity_id": str(request.activity_id),
                    "hardness": "medium", # Default
                    "marks": 1, # Default
                    "is_in_draft": False
                }
                
                # Insert into gen_questions
                res = supabase.table("gen_questions").insert(insert_data).execute()
                
                if res.data and len(res.data) > 0:
                    new_question_id = res.data[0]['id']
                    
                    # Insert into gen_questions_concepts_maps
                    # We need to link this question to all concept_ids in the request
                    # Assuming concept_ids are valid UUIDs existing in concepts table (referential integrity)
                    if request.concept_ids:
                        map_inserts = [
                            {
                                "gen_question_id": new_question_id,
                                "concept_id": str(cid)
                            } for cid in request.concept_ids
                        ]
                        supabase.table("gen_questions_concepts_maps").insert(map_inserts).execute()
                        
                    generated_count += 1
                
            except Exception as e:
                logger.error(f"Error generating/storing question of type {q_type}: {e}")

    return GenerateQuestionsResponse(
        success=True,
        message=f"Successfully generated and stored {generated_count} questions.",
        data={}
    )

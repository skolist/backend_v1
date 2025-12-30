import logging
import uuid
from typing import List, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

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
def generate_questions(request: GenerateQuestionsRequest):
    generated_questions = []
    
    # Map question types to mocker functions
    # Note: MSQ is not in req.md "Enum: Question Types" but present in mocker.py
    # req.md says: MCQ, SHORT_ANSWER, LONG_ANSWER, TRUE_FALSE, FILL_IN_THE_BLANK
    # mocker.py has: generate_mcq, generate_msq, generate_fill_in_the_blank, generate_true_false, generate_short_answer, generate_long_answer
    
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
            # The mocker doesn't use args yet, but we pass them as per requirement "gives the requirements to the mocker generate functions"
            try:
                # We are passing the config and other details to the mocker, 
                # although the current mocker implementation ignores them.
                # In a real implementation, we would pass these.
                question_obj = generator_func(
                    activity_id=request.activity_id,
                    concept_ids=request.concept_ids,
                    difficulty=request.config.difficulty_distribution # simplified choice logic would go here
                )
                
                # The mocker returns Pydantic models. We need to convert them to dict or compatible structure.
                # However, the Response Format in req.md defines a specific structure.
                # The mocker returns objects like MCQ4, which have specific fields.
                # The req.md response structure expects fields like 'id', 'type', 'marks', etc.
                # The schemas in ai.schemas.questions DO NOT have 'id', 'type', 'marks', 'hardness', 'concept_ids'.
                # They only have question, answers, explanation.
                
                # So we need to wrap the result from mocker into the expected response format.
                
                q_data = question_obj.model_dump()
                
                # Synthesize the missing fields for the response to match req.md
                # Since this is a mocker integration, we can mock these IDs and metadata.
                
                formatted_question = {
                    "id": str(uuid.uuid4()),
                    "type": q_type,
                    "text": q_data.get("question", ""),
                    "marks": 1, # Default mock
                    "hardness": "medium", # Default mock
                    "concept_ids": [str(cid) for cid in request.concept_ids],
                    "explanation": q_data.get("explanation", ""),
                    # Handle options/answers specific structure
                }
                
                # Add type specific fields
                if q_type == "MCQ":
                    formatted_question["options"] = [
                        {"id": "opt-1", "text": q_data.get("option1"), "isCorrect": q_data.get("answer") == 1},
                        {"id": "opt-2", "text": q_data.get("option2"), "isCorrect": q_data.get("answer") == 2},
                        {"id": "opt-3", "text": q_data.get("option3"), "isCorrect": q_data.get("answer") == 3},
                        {"id": "opt-4", "text": q_data.get("option4"), "isCorrect": q_data.get("answer") == 4},
                    ]
                    # Map integer answer to text if needed, or keep as is. req.md example shows "answer": "Acceleration" (text)
                    # For now, let's just stick to what we can extract.
                    # req.md says "answer": "The correct answer key or model answer."
                    # For MCQ, it seems to be the text of the correct option.
                    correct_idx = q_data.get("answer")
                    formatted_question["answer"] = q_data.get(f"option{correct_idx}")

                elif q_type == "MSQ": # Not in req.md but in mocker
                     formatted_question["options"] = [
                        {"id": "opt-1", "text": q_data.get("option1"), "isCorrect": 1 in q_data.get("answers", [])},
                        {"id": "opt-2", "text": q_data.get("option2"), "isCorrect": 2 in q_data.get("answers", [])},
                        {"id": "opt-3", "text": q_data.get("option3"), "isCorrect": 3 in q_data.get("answers", [])},
                        {"id": "opt-4", "text": q_data.get("option4"), "isCorrect": 4 in q_data.get("answers", [])},
                    ]
                     formatted_question["answer"] = ", ".join([q_data.get(f"option{i}") for i in q_data.get("answers", [])])

                elif q_type == "TRUE_FALSE":
                    formatted_question["options"] = [
                        {"id": "tf-1", "text": "True", "isCorrect": q_data.get("answer") is True},
                        {"id": "tf-2", "text": "False", "isCorrect": q_data.get("answer") is False}
                    ]
                    formatted_question["answer"] = str(q_data.get("answer"))

                elif q_type == "FILL_IN_THE_BLANK":
                    formatted_question["options"] = []
                    formatted_question["answer"] = q_data.get("answer")

                elif q_type in ["SHORT_ANSWER", "LONG_ANSWER"]:
                    formatted_question["options"] = []
                    formatted_question["answer"] = q_data.get("answer")

                generated_questions.append(formatted_question)
                
            except Exception as e:
                logger.error(f"Error generating question of type {q_type}: {e}")
                # Continue or raise? For now continue.

    return GenerateQuestionsResponse(
        success=True,
        message=f"Successfully generated {len(generated_questions)} questions.",
        data={"questions": generated_questions}
    )

import logging
from typing import List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from supabase import Client

from api.v1.auth import get_supabase_client
from .dependencies import require_admin
# Reuse helper to format questions same as QGen
from api.v1.qgen.generate_questions.utils.fetch_questions import extract_bank_question_to_gen_payload, QuestionRequestType

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/bank",
    tags=["bank_management"],
    dependencies=[Depends(require_admin)]
)

class BankFilter(BaseModel):
    subject_id: Optional[str] = None
    question_type: Optional[str] = None
    hardness_level: Optional[str] = None
    is_solved_example: Optional[bool] = None
    is_from_exercise: Optional[bool] = None
    is_image_needed: Optional[bool] = None
    is_incomplete: Optional[bool] = None
    concept_ids: Optional[List[str]] = None
    search_query: Optional[str] = None

class ListQuestionsRequest(BaseModel):
    page: int = 1
    page_size: int = 20
    filters: BankFilter

class BankQuestionResponse(BaseModel):
    id: str
    question: dict # The formatted payload for GeneratedQuestionCard
    concept_ids: List[str]
    raw_data: dict # Original bank question data

class ListQuestionsResponse(BaseModel):
    data: List[BankQuestionResponse]
    total: int
    page: int
    page_size: int

@router.post("/list", response_model=ListQuestionsResponse)
async def list_bank_questions(
    request: ListQuestionsRequest,
    supabase: Client = Depends(get_supabase_client)
):
    """
    Fetch paginated list of bank questions with filters.
    """
    try:
        # Base query
        query = supabase.table("bank_questions").select("*", count="exact")
        
        # Apply Filters
        if request.filters.subject_id:
            query = query.eq("subject_id", request.filters.subject_id)
            
        if request.filters.question_type:
            query = query.eq("question_type", request.filters.question_type)
            
        if request.filters.hardness_level:
            query = query.eq("hardness_level", request.filters.hardness_level)
            
        if request.filters.is_solved_example is not None:
            query = query.eq("is_solved_example", request.filters.is_solved_example)
            
        if request.filters.is_from_exercise is not None:
             query = query.eq("is_from_exercise", request.filters.is_from_exercise)

        if request.filters.is_image_needed is not None:
             query = query.eq("is_image_needed", request.filters.is_image_needed)

        if request.filters.is_incomplete is not None:
             query = query.eq("is_incomplete", request.filters.is_incomplete)
             
        if request.filters.search_query:
            # Simple text search on question_text
            query = query.ilike("question_text", f"%{request.filters.search_query}%")

        # Concept filtering logic
        # Since bank_questions doesn't have concept_ids array column, we need to filter by ID
        # if the user provides concept filters. 
        # This usually allows filtering by ONE list of concepts (OR logic? or AND?)
        # For simplicity, if concept_ids are provided, we find question IDs that match ANY of them
        # using the mapping table, then filter main query by those IDs.
        
        if request.filters.concept_ids and len(request.filters.concept_ids) > 0:
            map_res = supabase.table("bank_questions_concepts_maps")\
                .select("bank_question_id")\
                .in_("concept_id", request.filters.concept_ids)\
                .execute()
            
            valid_ids = [row['bank_question_id'] for row in map_res.data]
            if not valid_ids:
                return ListQuestionsResponse(data=[], total=0, page=request.page, page_size=request.page_size)
            
            query = query.in_("id", valid_ids)

        # Pagination
        start = (request.page - 1) * request.page_size
        end = start + request.page_size - 1
        
        query = query.range(start, end).order("created_at", desc=True)
        
        # Execute
        response = query.execute()
        
        # Determine strict request type for formatting (fallback to SOLVED if both false or mixed)
        # This is mainly for the 'is_solved_example' flag in the payload
        req_type_enum = QuestionRequestType.SOLVED_EXAMPLE
        if request.filters.is_from_exercise:
            req_type_enum = QuestionRequestType.EXERCISE_QUESTION
            
        # Format response
        formatted_list = []
        for item in response.data:
            # We need to fetch concepts for each question to display them
            # This is N+1 problem potential, but for page_size=20 it's acceptable for admin tool.
            # OR we can do a second query to fetch all concepts for these 20 IDs.
            
            # Formatted payload (reuses logic from fetch_questions)
            # logic expects a request_type to set is_solved/is_exercise flags in the payload.
            # We can infer it from the specific item
            item_req_type = QuestionRequestType.SOLVED_EXAMPLE if item.get("is_solved_example") else QuestionRequestType.EXERCISE_QUESTION
            
            payload = extract_bank_question_to_gen_payload(item, item_req_type)
            
            # Fetch concepts:
            # Using a separate query or if we could join in the main query
            # Supabase-py join syntax: .select("*, bank_questions_concepts_maps(concept_id)")
            # Let's assume we didn't do join above to keep count clean, so we do it now or 
            # ideally we should have done it in the main query.
            
            # Let's optimize: fetch concepts for these IDs in batch if possible, or just lazy load.
            # For admin UI, let's just do individual fetch or rely on what we have. 
            # Actually, extract_bank_question_to_gen_payload doesn't put concepts in payload.
            # The GeneratedQuestionCard needs 'concepts' list to display badges.
            # 'concept_ids' list is side-loaded.
            
            formatted_list.append({
                "id": item["id"],
                "question": payload, # The 'inner' question data with text, options etc.
                "concept_ids": [], # Will populate this if we fetch maps
                "raw_data": item
            })
            
        # Optimization: Fetch concepts for all these questions
        if response.data:
            q_ids = [q["id"] for q in response.data]
            maps = supabase.table("bank_questions_concepts_maps")\
                .select("bank_question_id, concept_id")\
                .in_("bank_question_id", q_ids)\
                .execute()
                
            # Group by question
            q_to_concepts = {}
            for m in maps.data:
                qid = m["bank_question_id"]
                if qid not in q_to_concepts:
                    q_to_concepts[qid] = []
                q_to_concepts[qid].append(m["concept_id"])
                
            # Attach to list
            for q in formatted_list:
                q["concept_ids"] = q_to_concepts.get(q["id"], [])

        return ListQuestionsResponse(
            data=formatted_list,
            total=response.count or 0,
            page=request.page,
            page_size=request.page_size
        )
    except Exception as e:
        logger.error(f"Error fetching bank questions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error fetching questions"
        )

# ============================================================================
# PREVIEW ENDPOINTS (No Save)
# ============================================================================

import os
from google import genai
from google.genai import types
from api.v1.qgen.auto_correct.service import AutoCorrectService
from api.v1.qgen.regenerate_question import process_question_and_validate
from supabase_dir import BankQuestionsUpdate

class PreviewRequest(BaseModel):
    question: dict # The question payload (Generations format)

class CompareResponse(BaseModel):
    original: dict
    new: dict

@router.post("/preview/auto-correct", response_model=CompareResponse)
async def preview_auto_correct(
    request: PreviewRequest,
    supabase: Client = Depends(get_supabase_client)
):
    """
    Run auto-correct on the question but DO NOT save.
    Returns both original and new version for comparison.
    """
    gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    
    # We use valid image_part=None for now as we don't have the screenshot here easily
    # The AutoCorrectService handles optional image.
    
    try:
        # Reuse the service logic
        corrected_q = await AutoCorrectService.process_and_validate(
            gemini_client=gemini_client,
            gen_question_data=request.question,
            image_part=None, 
            retry_idx=0
        )
        
        # Convert Pydantic model to dict
        new_data = corrected_q.model_dump(exclude_none=True)
        
        # Merge with ID/Metadata from original to keep it consistent
        merged_new = {**request.question, **new_data}
        
        return CompareResponse(
            original=request.question,
            new=merged_new
        )
    except Exception as e:
        logger.error(f"Auto-correct preview failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class RegeneratePreviewRequest(BaseModel):
    question: dict
    prompt: Optional[str] = None
    # No file support for now in this simple preview

@router.post("/preview/regenerate", response_model=CompareResponse)
async def preview_regenerate(
    request: RegeneratePreviewRequest,
    supabase: Client = Depends(get_supabase_client)
):
    """
    Run regenerate on the question but DO NOT save.
    """
    gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    
    try:
        # Reuse regenerate logic
        # process_question_and_validate uses the prompt generator internally which reads CustomInstruction or prompt
        # If we want to support custom prompt, we might need to inject it into the question payload
        # or use a lower level function. 
        # regenerate_question_prompt uses 'custom_instructions' from the dict if present.
        
        q_data = request.question.copy()
        if request.prompt:
            # Inject prompt as if it was a custom instruction or context
            # The prompt generator might need adjustment if we strictly want "User Prompt" style
            # But usually it uses fields available.
            # Let's assume we update the instruction field for the prompt
            q_data["question_text"] = f"{q_data.get('question_text')} \n\nInstruction: {request.prompt}"

        new_q = await process_question_and_validate(
            gemini_client=gemini_client,
            gen_question_data=q_data,
            retry_idx=0
        )
        
        new_data = new_q.model_dump(exclude_none=True)
        merged_new = {**request.question, **new_data}
        
        return CompareResponse(
            original=request.question,
            new=merged_new
        )
    except Exception as e:
        logger.error(f"Regenerate preview failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# PERSISTENCE
# ============================================================================

class UpdateBankQuestionRequest(BaseModel):
    id: str
    question: dict # The final approved question payload

@router.post("/update")
async def update_bank_question(
    request: UpdateBankQuestionRequest,
    supabase: Client = Depends(get_supabase_client)
):
    """
    Persist changes to bank_questions table.
    """
    q_data = request.question
    
    # Map GenQuestions format back to BankQuestions format
    # 1. match_the_following_columns -> match_columns
    match_cols = q_data.pop("match_the_following_columns", None)
    
    # 2. SVGs list -> svgs text? 
    # Bank schema says 'svgs' is str. 
    # Gen payload usually has 'svgs' as list of dicts or objects.
    svg_list = q_data.pop("svgs", None)
    
    update_payload = {
        "question_text": q_data.get("question_text"),
        "answer_text": q_data.get("answer_text"),
        "explanation": q_data.get("explanation"),
        "marks": q_data.get("marks"),
        "hardness_level": q_data.get("hardness_level"),
        "question_type": q_data.get("question_type"),
        
        "option1": q_data.get("option1"),
        "option2": q_data.get("option2"),
        "option3": q_data.get("option3"),
        "option4": q_data.get("option4"),
        
        "correct_mcq_option": q_data.get("correct_mcq_option"),
        "msq_option1_answer": q_data.get("msq_option1_answer"),
        "msq_option2_answer": q_data.get("msq_option2_answer"),
        "msq_option3_answer": q_data.get("msq_option3_answer"),
        "msq_option4_answer": q_data.get("msq_option4_answer"),
        
        # match_columns handling
        # If match_cols is dict, we might need to stringify it if DB expects string
        # Assuming Supabase/Postgres handles JSON/Dict mapping if column is compatible
        "match_columns": match_cols if match_cols else None,
        
        # svgs handling
        # If we have list, we might just store it as is if DB handles it, or JSON stringify
        # Usually for bank, we just keep it simple.
        # Logic: If we received new SVGs, we update. 
        # CAUTION: 'svgs' column in schema is 'str'.
        # We should probably JSON stringify if list.
        "svgs": str(svg_list) if svg_list else None 
    }
    
    # Remove None values to avoid overwriting with nulls if intent was partial update?
    # No, this is a full update of the question content (Replace).
    # But clean up keys that are strictly None to rely on DB defaults? 
    # Better to update what we have.
    
    try:
        # Validate with Pydantic Schema
        # Use BankQuestionsUpdate (from supabase_dir)
        # We need to filter keys that are not in valid schema
        valid_keys = BankQuestionsUpdate.model_fields.keys()
        final_payload = {k: v for k, v in update_payload.items() if k in valid_keys}
        
        supabase.table("bank_questions").update(final_payload).eq("id", request.id).execute()
        
        return {"status": "success", "id": request.id}
        
    except Exception as e:
        logger.error(f"Failed to update bank question: {e}")
        raise HTTPException(status_code=500, detail=str(e))

class QuestionIdRequest(BaseModel):
    id: str

@router.post("/remove_image_needed")
async def remove_image_needed(
    request: QuestionIdRequest,
    supabase: Client = Depends(get_supabase_client)
):
    try:
        supabase.table("bank_questions").update({"is_image_needed": False}).eq("id", request.id).execute()
        return {"status": "success", "id": request.id}
    except Exception as e:
        logger.error(f"Failed to remove image needed flag: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/remove_incomplete")
async def remove_incomplete(
    request: QuestionIdRequest,
    supabase: Client = Depends(get_supabase_client)
):
    try:
        supabase.table("bank_questions").update({"is_incomplete": False}).eq("id", request.id).execute()
        return {"status": "success", "id": request.id}
    except Exception as e:
        logger.error(f"Failed to remove incomplete flag: {e}")
        raise HTTPException(status_code=500, detail=str(e))

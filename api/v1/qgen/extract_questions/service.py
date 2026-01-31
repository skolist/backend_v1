"""
Service layer for extracting questions from files.
"""

import logging
import os
from typing import Optional, List

import supabase
from google import genai
from google.genai import types
from fastapi import UploadFile

from api.v1.qgen.models import ExtractedQuestionsList, QUESTION_TYPE_TO_ENUM
from api.v1.qgen.prompts import extract_questions_prompt
from supabase_dir import (
    GenQuestionsInsert,
    GenImagesInsert,
    QgenDraftSectionsInsert,
    PublicHardnessLevelEnumEnum,
)

logger = logging.getLogger(__name__)


class ExtractionProcessingError(Exception):
    """Raised when extraction processing fails."""
    pass


class ExtractionValidationError(Exception):
    """Raised when extracted questions fail validation."""
    pass


async def process_uploaded_file(file: UploadFile) -> types.Part:
    """
    Process an uploaded file and convert it to a Gemini Part object.
    
    Args:
        file: The uploaded file (image or PDF)
        
    Returns:
        Gemini Part object
    """
    if not file.filename or not file.size or file.size == 0:
        raise ExtractionValidationError("Empty or invalid file uploaded")
    
    content = await file.read()
    content_type = file.content_type or "application/octet-stream"
    
    # Validate file type
    allowed_types = [
        "image/png", "image/jpeg", "image/jpg", "image/gif", "image/webp",
        "application/pdf"
    ]
    
    if content_type not in allowed_types:
        raise ExtractionValidationError(
            f"Unsupported file type: {content_type}. Allowed: images (png, jpeg, gif, webp) and PDF"
        )
    
    await file.seek(0)
    return types.Part.from_bytes(data=content, mime_type=content_type)


class ExtractQuestionsService:
    """Service for extracting questions from files using LLM."""

    @staticmethod
    async def process_extraction(
        gemini_client: genai.Client,
        file_part: types.Part,
        custom_prompt: Optional[str] = None,
        retry_idx: int = None,
    ) -> ExtractedQuestionsList:
        """
        Process file and extract questions using Gemini.
        
        Args:
            gemini_client: Gemini API client
            file_part: File as Gemini Part object
            custom_prompt: Optional user instructions
            retry_idx: Retry attempt number for logging
            
        Returns:
            ExtractedQuestionsList with parsed questions
        """
        prompt_text = extract_questions_prompt(custom_prompt)
        
        contents = [file_part, types.Part.from_text(text=prompt_text)]
        
        response = await gemini_client.aio.models.generate_content(
            model="gemini-2.5-flash",
            contents=contents,
            config={
                "response_mime_type": "application/json",
                "response_schema": ExtractedQuestionsList,
            },
        )
        
        try:
            return response.parsed
        except Exception as e:
            raise ExtractionValidationError(f"Failed to parse LLM response: {e}")

    @staticmethod
    async def extract_and_insert(
        file: UploadFile,
        activity_id: str,
        qgen_draft_id: str,
        supabase_client: supabase.Client,
        section_name: Optional[str] = None,
        custom_prompt: Optional[str] = None,
    ) -> dict:
        """
        Main extraction flow: process file, extract questions, create section, insert to DB.
        
        Args:
            file: Uploaded file (image/PDF)
            activity_id: Activity UUID
            qgen_draft_id: Draft UUID
            supabase_client: Supabase client
            section_name: Optional name for new section
            custom_prompt: Optional user instructions for extraction
            
        Returns:
            Dict with section_id, section_name, questions_extracted count
        """
        # 1. Process file
        logger.info(f"Processing file for extraction: {file.filename}")
        file_part = await process_uploaded_file(file)
        
        # 2. Initialize Gemini client
        gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        
        # 3. Call LLM with retry
        max_retries = 5
        last_exception = None
        extracted_result = None
        
        for attempt in range(max_retries):
            try:
                extracted_result = await ExtractQuestionsService.process_extraction(
                    gemini_client, file_part, custom_prompt, attempt + 1
                )
                break
            except Exception as e:
                last_exception = e
                logger.warning(f"Extraction attempt {attempt + 1} failed: {e}")
        
        if extracted_result is None:
            raise ExtractionProcessingError(
                f"Extraction failed after {max_retries} retries"
            ) from last_exception
        
        questions = extracted_result.questions
        
        if not questions:
            logger.info("No questions extracted from file")
            return {
                "section_id": None,
                "section_name": None,
                "questions_extracted": 0,
                "questions": [],
            }
        
        # 4. Get max position for new section
        existing_sections = (
            supabase_client.table("qgen_draft_sections")
            .select("position_in_draft")
            .eq("qgen_draft_id", qgen_draft_id)
            .order("position_in_draft", desc=True)
            .limit(1)
            .execute()
        )
        
        max_position = 0
        if existing_sections.data:
            max_position = existing_sections.data[0].get("position_in_draft", 0)
        
        # 5. Create new section
        final_section_name = section_name or "Extracted Questions"
        new_section = QgenDraftSectionsInsert(
            qgen_draft_id=qgen_draft_id,
            section_name=final_section_name,
            position_in_draft=max_position + 1,
        )
        
        section_result = (
            supabase_client.table("qgen_draft_sections")
            .insert(new_section.model_dump(mode="json", exclude_none=True))
            .execute()
        )
        
        if not section_result.data:
            raise ExtractionProcessingError("Failed to create draft section")
        
        section_id = section_result.data[0]["id"]
        logger.info(f"Created new section: {section_id} with name: {final_section_name}")
        
        # 6. Insert questions
        inserted_questions = []
        difficulty_mapping = {
            "easy": PublicHardnessLevelEnumEnum.EASY,
            "medium": PublicHardnessLevelEnumEnum.MEDIUM,
            "hard": PublicHardnessLevelEnumEnum.HARD,
        }
        
        for position, question in enumerate(questions, start=1):
            try:
                # Map question_type string to enum
                question_type_enum = QUESTION_TYPE_TO_ENUM.get(question.question_type)
                if not question_type_enum:
                    logger.warning(f"Unknown question type: {question.question_type}, skipping")
                    continue
                
                # Build question data
                question_data = question.model_dump(exclude_none=True)
                
                # Remove fields not in gen_questions table
                svg_list = question_data.pop("svgs", None)
                question_data.pop("question_type", None)  # We use the enum instead
                
                # Set hardness level
                hardness_str = question_data.pop("hardness_level", "medium")
                hardness_level = difficulty_mapping.get(
                    hardness_str.lower() if hardness_str else "medium",
                    PublicHardnessLevelEnumEnum.MEDIUM
                )
                
                # Handle marks - pop from dict and use default if not present
                marks_value = question_data.pop("marks", 1)
                
                # Handle answer_text - required field, provide default if missing
                answer_text_value = question_data.pop("answer_text", "") or ""
                
                # Create insert model
                gen_question = GenQuestionsInsert(
                    **question_data,
                    activity_id=activity_id,
                    question_type=question_type_enum,
                    hardness_level=hardness_level,
                    qgen_draft_section_id=section_id,
                    position_in_section=position,
                    is_in_draft=True,
                    marks=marks_value,
                    answer_text=answer_text_value,
                )
                
                # Insert question
                result = (
                    supabase_client.table("gen_questions")
                    .insert(gen_question.model_dump(mode="json", exclude_none=True))
                    .execute()
                )
                
                if result.data:
                    inserted_question = result.data[0]
                    question_id = inserted_question["id"]
                    
                    inserted_questions.append({
                        "id": question_id,
                        "question_type": question.question_type,
                    })
                    
                    # Insert SVGs if present
                    if svg_list:
                        for svg_position, svg_item in enumerate(svg_list, start=1):
                            try:
                                svg_string = (
                                    svg_item.get("svg") 
                                    if isinstance(svg_item, dict) 
                                    else svg_item.svg
                                )
                                if svg_string:
                                    gen_image = GenImagesInsert(
                                        gen_question_id=question_id,
                                        svg_string=svg_string,
                                        position=svg_position,
                                    )
                                    supabase_client.table("gen_images").insert(
                                        gen_image.model_dump(mode="json", exclude_none=True)
                                    ).execute()
                            except Exception as svg_error:
                                logger.warning(
                                    f"Failed to insert SVG for question {question_id}: {svg_error}"
                                )
                
            except Exception as q_error:
                logger.warning(f"Failed to insert question at position {position}: {q_error}")
                continue
        
        logger.info(
            f"Extraction complete: {len(inserted_questions)} questions inserted into section {section_id}"
        )
        
        return {
            "section_id": section_id,
            "section_name": final_section_name,
            "questions_extracted": len(inserted_questions),
            "questions": inserted_questions,
        }

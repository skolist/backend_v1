import logging
from typing import Optional
from datetime import time
import supabase
from fastapi import HTTPException

logger = logging.getLogger(__name__)

def format_duration(d_time: Optional[time]) -> str:
    if not d_time:
        return "60 Mins"
    if isinstance(d_time, str):
        # Handle cases where it might be a string from database
        try:
            from datetime import datetime
            extra_time = datetime.strptime(d_time, "%H:%M:%S").time()
            total_minutes = extra_time.hour * 60 + extra_time.minute
            return f"{total_minutes} Mins" if total_minutes > 0 else "60 Mins"
        except:
            return d_time
            
    total_minutes = d_time.hour * 60 + d_time.minute
    return f"{total_minutes} Mins" if total_minutes > 0 else "60 Mins"

async def fetch_paper_data(draft_id: str, supabase_client: supabase.Client):
    """
    Fetches all data required to generate a paper (Draft, Sections, Questions, Instructions, Images).
    """
    try:
        # 1. Fetch Draft Data
        draft_res = supabase_client.table("qgen_drafts").select("*").eq("id", draft_id).execute()
        if not draft_res.data:
            raise HTTPException(status_code=404, detail="Draft not found")
        draft = draft_res.data[0]

        # 2. Fetch Sections
        sections_res = supabase_client.table("qgen_draft_sections").select("*").eq("qgen_draft_id", draft_id).order("position_in_draft").execute()
        sections = sections_res.data

        # 3. Fetch Instructions
        instructions_res = supabase_client.table("qgen_draft_instructions_drafts_maps").select("*").eq("qgen_draft_id", draft_id).order("created_at", desc=True).execute()
        instructions = instructions_res.data

        # 4. Fetch Questions
        section_ids = [s["id"] for s in sections]
        questions = []
        if section_ids:
            questions_res = supabase_client.table("gen_questions").select("*").eq("is_in_draft", True).in_("qgen_draft_section_id", section_ids).execute()
            questions = questions_res.data

        # 5. Fetch Question Images
        question_ids = [q["id"] for q in questions]
        images_map = {}
        if question_ids:
            images_res = supabase_client.table("gen_images").select("*").in_("gen_question_id", question_ids).order("position").execute()
            for img in images_res.data:
                q_id = img["gen_question_id"]
                if q_id not in images_map:
                    images_map[q_id] = []
                images_map[q_id].append(img)

        # 6. Get Logo URL if exists
        logo_url = None
        if draft.get("logo_url"):
            try:
                logo_res = supabase_client.storage.from_("draft_logo_bucket").create_signed_url(draft["logo_url"], 3600)
                logo_url = logo_res.get("signedUrl")
            except Exception as e:
                logger.warning(f"Failed to get signed logo URL: {e}")

        return {
            "draft": draft,
            "sections": sections,
            "questions": questions,
            "instructions": instructions,
            "logo_url": logo_url,
            "images_map": images_map
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Database error during paper data fetching")
        raise HTTPException(status_code=500, detail="Internal Server Error") from e

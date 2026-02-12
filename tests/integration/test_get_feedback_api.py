"""
Integration tests for the get_feedback API endpoint.

Tests the AI-generated feedback functionality for question drafts.
"""

import uuid
from typing import Any, Dict, List

import pytest
from fastapi.testclient import TestClient
from supabase import Client
from supabase_dir import (
    GenQuestionsInsert,
    PublicHardnessLevelEnumEnum,
    PublicQuestionTypeEnumEnum,
    QgenDraftSectionsInsert,
)

# ============================================================================
# AUTH TESTS
# ============================================================================


class TestGetFeedbackAuth:
    """Tests for authentication on the get_feedback endpoint."""

    def test_returns_401_without_auth_token(
        self,
        unauthenticated_test_client: TestClient,
    ):
        """Test that the endpoint returns 401 when no auth token is provided."""
        response = unauthenticated_test_client.post(
            "/api/v1/qgen/get_feedback",
            json={"draft_id": str(uuid.uuid4())},
        )
        assert response.status_code == 401


# ============================================================================
# VALIDATION TESTS
# ============================================================================


class TestGetFeedbackValidation:
    """Tests for request validation on the get_feedback endpoint."""

    def test_returns_422_for_missing_draft_id(
        self,
        test_client: TestClient,
    ):
        """Test that the endpoint returns 422 when draft_id is missing."""
        response = test_client.post(
            "/api/v1/qgen/get_feedback",
            json={},
        )
        assert response.status_code == 422

    def test_returns_404_for_nonexistent_draft(
        self,
        test_client: TestClient,
    ):
        """Test that the endpoint returns 404 for a non-existent draft."""
        response = test_client.post(
            "/api/v1/qgen/get_feedback",
            json={"draft_id": str(uuid.uuid4())},
        )
        assert response.status_code == 404


# ============================================================================
# FUNCTIONAL TESTS
# ============================================================================


class TestGetFeedbackFunctional:
    """Functional tests for the get_feedback endpoint."""

    @pytest.fixture
    def test_draft_with_questions(
        self,
        service_supabase_client: Client,
        test_activity: Dict[str, Any],
    ):
        """Create a test draft with questions for feedback testing."""
        section_id = str(uuid.uuid4())
        
        # Get the auto-created draft for this activity (created by trigger)
        draft_resp = service_supabase_client.table("qgen_drafts").select("id").eq(
            "activity_id", test_activity["id"]
        ).execute()
        
        if not draft_resp.data:
            pytest.skip("No draft found for test activity")
        
        draft_id = draft_resp.data[0]["id"]
        
        # Create section using typed model
        section_data = QgenDraftSectionsInsert(
            id=uuid.UUID(section_id),
            qgen_draft_id=uuid.UUID(draft_id),
            section_name="Test Section",
            position_in_draft=1,
        )
        service_supabase_client.table("qgen_draft_sections").insert(
            section_data.model_dump(mode="json", exclude_none=True)
        ).execute()
        
        # Create questions in the section (need at least 5 for feedback)
        question_ids = []
        for i in range(6):
            q_id = str(uuid.uuid4())
            question_ids.append(q_id)
            question_data = GenQuestionsInsert(
                id=uuid.UUID(q_id),
                activity_id=uuid.UUID(test_activity["id"]),
                qgen_draft_section_id=uuid.UUID(section_id),
                question_type=PublicQuestionTypeEnumEnum.MCQ4,
                question_text=f"Test question {i+1}?",
                option1="Option A",
                option2="Option B",
                option3="Option C",
                option4="Option D",
                correct_mcq_option=1,
                answer_text="Option A",
                is_in_draft=True,
                hardness_level=PublicHardnessLevelEnumEnum.EASY,
                marks=1,
            )
            service_supabase_client.table("gen_questions").insert(
                question_data.model_dump(mode="json", exclude_none=True)
            ).execute()
        
        yield {
            "draft_id": draft_id,
            "section_id": section_id,
            "question_ids": question_ids,
        }
        
        # Cleanup (draft is auto-created, deleted via cascade with activity)
        service_supabase_client.table("gen_questions").delete().in_(
            "id", question_ids
        ).execute()
        service_supabase_client.table("qgen_draft_sections").delete().eq(
            "id", section_id
        ).execute()

    def test_returns_feedback_for_valid_draft(
        self,
        test_client: TestClient,
        test_draft_with_questions: Dict[str, Any],
    ):
        """Test that the endpoint returns feedback for a valid draft with questions."""
        response = test_client.post(
            "/api/v1/qgen/get_feedback",
            json={"draft_id": test_draft_with_questions["draft_id"]},
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should return FeedbackList with .feedbacks list
        assert "feedbacks" in data
        assert isinstance(data["feedbacks"], list)
        assert len(data["feedbacks"]) > 0

    @pytest.fixture
    def test_draft_with_few_questions(
        self,
        service_supabase_client: Client,
        test_activity: Dict[str, Any],
    ):
        """Create a test draft with too few questions."""
        section_id = str(uuid.uuid4())
        
        # Get the auto-created draft for this activity (created by trigger)
        draft_resp = service_supabase_client.table("qgen_drafts").select("id").eq(
            "activity_id", test_activity["id"]
        ).execute()
        
        if not draft_resp.data:
            pytest.skip("No draft found for test activity")
        
        draft_id = draft_resp.data[0]["id"]
        
        # Create section using typed model
        section_data = QgenDraftSectionsInsert(
            id=uuid.UUID(section_id),
            qgen_draft_id=uuid.UUID(draft_id),
            section_name="Test Section",
            position_in_draft=1,
        )
        service_supabase_client.table("qgen_draft_sections").insert(
            section_data.model_dump(mode="json", exclude_none=True)
        ).execute()
        
        # Create only 2 questions (less than 5)
        question_ids = []
        for i in range(2):
            q_id = str(uuid.uuid4())
            question_ids.append(q_id)
            question_data = GenQuestionsInsert(
                id=uuid.UUID(q_id),
                activity_id=uuid.UUID(test_activity["id"]),
                qgen_draft_section_id=uuid.UUID(section_id),
                question_type=PublicQuestionTypeEnumEnum.MCQ4,
                question_text=f"Test question {i+1}?",
                option1="Option A",
                option2="Option B",
                option3="Option C",
                option4="Option D",
                correct_mcq_option=1,
                answer_text="Option A",
                is_in_draft=True,
                hardness_level=PublicHardnessLevelEnumEnum.EASY,
                marks=1,
            )
            service_supabase_client.table("gen_questions").insert(
                question_data.model_dump(mode="json", exclude_none=True)
            ).execute()
        
        yield {
            "draft_id": draft_id,
            "section_id": section_id,
            "question_ids": question_ids,
        }
        
        # Cleanup (draft is auto-created, deleted via cascade with activity)
        service_supabase_client.table("gen_questions").delete().in_(
            "id", question_ids
        ).execute()
        service_supabase_client.table("qgen_draft_sections").delete().eq(
            "id", section_id
        ).execute()

    def test_returns_400_for_insufficient_questions(
        self,
        test_client: TestClient,
        test_draft_with_few_questions: Dict[str, Any],
    ):
        """Test that the endpoint returns 400 when draft has less than 5 questions."""
        response = test_client.post(
            "/api/v1/qgen/get_feedback",
            json={"draft_id": test_draft_with_few_questions["draft_id"]},
        )
        
        # Should return 400 for insufficient questions
        assert response.status_code == 400

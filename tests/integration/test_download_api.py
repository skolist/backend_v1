"""
Integration tests for the download_pdf and download_docx API endpoints.

Tests the document generation functionality.
"""

import uuid
from typing import Any, Dict

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
# FIXTURES
# ============================================================================


@pytest.fixture
def test_draft_with_section(
    service_supabase_client: Client,
    test_activity: Dict[str, Any],
):
    """Create a test draft with a section and questions for download testing."""
    section_id = str(uuid.uuid4())
    
    # Get the auto-created draft for this activity (created by trigger on activity insert)
    draft_resp = service_supabase_client.table("qgen_drafts").select("id").eq(
        "activity_id", test_activity["id"]
    ).execute()
    
    if not draft_resp.data:
        pytest.skip("No draft found for test activity")
    
    draft_id = draft_resp.data[0]["id"]
    
    # Create section (column is 'section_name' and 'position_in_draft')
    section_data = QgenDraftSectionsInsert(
        id=uuid.UUID(section_id),
        qgen_draft_id=uuid.UUID(draft_id),
        section_name="Test Section",
        position_in_draft=1,
    )
    service_supabase_client.table("qgen_draft_sections").insert(
        section_data.model_dump(mode="json", exclude_none=True)
    ).execute()
    
    # Create questions
    question_ids = []
    for i in range(3):
        q_id = str(uuid.uuid4())
        question_ids.append(q_id)
        question_data = GenQuestionsInsert(
            id=uuid.UUID(q_id),
            activity_id=uuid.UUID(test_activity["id"]),
            qgen_draft_section_id=uuid.UUID(section_id),
            question_type=PublicQuestionTypeEnumEnum.MCQ4,
            question_text=f"What is {i+1} + {i+1}?",
            option1=str(i * 2),
            option2=str((i + 1) * 2),
            option3=str((i + 2) * 2),
            option4=str((i + 3) * 2),
            correct_mcq_option=2,
            answer_text=str((i + 1) * 2),
            marks=1,
            is_in_draft=True,
            hardness_level=PublicHardnessLevelEnumEnum.EASY,
        )
        service_supabase_client.table("gen_questions").insert(
            question_data.model_dump(mode="json", exclude_none=True)
        ).execute()
    
    yield {
        "draft_id": draft_id,
        "section_id": section_id,
        "question_ids": question_ids,
        "activity_id": test_activity["id"],
    }
    
    # Cleanup (draft is auto-created with activity, deleted via cascade)
    service_supabase_client.table("gen_questions").delete().in_(
        "id", question_ids
    ).execute()
    service_supabase_client.table("qgen_draft_sections").delete().eq(
        "id", section_id
    ).execute()


# ============================================================================
# DOWNLOAD PDF TESTS
# ============================================================================


class TestDownloadPDFAuth:
    """Tests for authentication on the download_pdf endpoint."""

    def test_returns_401_without_auth_token(
        self,
        unauthenticated_test_client: TestClient,
    ):
        """Test that the endpoint returns 401 when no auth token is provided."""
        response = unauthenticated_test_client.post(
            "/api/v1/qgen/download_pdf",
            json={
                "draft_id": str(uuid.uuid4()),
                "mode": "answer",
            },
        )
        assert response.status_code == 401


class TestDownloadPDFValidation:
    """Tests for request validation on the download_pdf endpoint."""

    def test_returns_422_for_missing_draft_id(
        self,
        test_client: TestClient,
    ):
        """Test that the endpoint returns 422 when draft_id is missing."""
        response = test_client.post(
            "/api/v1/qgen/download_pdf",
            json={
                "mode": "answer",
            },
        )
        assert response.status_code == 422

    def test_returns_404_for_nonexistent_draft(
        self,
        test_client: TestClient,
    ):
        """Test that the endpoint returns 404 for a non-existent draft."""
        response = test_client.post(
            "/api/v1/qgen/download_pdf",
            json={
                "draft_id": str(uuid.uuid4()),
                "mode": "answer",
            },
        )
        assert response.status_code == 404


class TestDownloadPDFFunctional:
    """Functional tests for the download_pdf endpoint."""

    @pytest.mark.slow
    def test_generates_pdf_with_questions_only(
        self,
        test_client: TestClient,
        test_draft_with_section: Dict[str, Any],
    ):
        """Test that the endpoint generates a PDF with questions only."""
        response = test_client.post(
            "/api/v1/qgen/download_pdf",
            json={
                "draft_id": test_draft_with_section["draft_id"],
                "mode": "paper",
            },
        )
        
        assert response.status_code == 200
        # PDF responses should have PDF content type
        assert "application/pdf" in response.headers.get("content-type", "")

    @pytest.mark.slow
    def test_generates_pdf_with_answers(
        self,
        test_client: TestClient,
        test_draft_with_section: Dict[str, Any],
    ):
        """Test that the endpoint generates a PDF with answers included."""
        response = test_client.post(
            "/api/v1/qgen/download_pdf",
            json={
                "draft_id": test_draft_with_section["draft_id"],
                "mode": "answer",
            },
        )
        
        assert response.status_code == 200
        assert "application/pdf" in response.headers.get("content-type", "")


# ============================================================================
# DOWNLOAD DOCX TESTS
# ============================================================================


class TestDownloadDOCXAuth:
    """Tests for authentication on the download_docx endpoint."""

    def test_returns_401_without_auth_token(
        self,
        unauthenticated_test_client: TestClient,
    ):
        """Test that the endpoint returns 401 when no auth token is provided."""
        response = unauthenticated_test_client.post(
            "/api/v1/qgen/download_docx",
            json={
                "draft_id": str(uuid.uuid4()),
                "mode": "answer",
            },
        )
        assert response.status_code == 401


class TestDownloadDOCXValidation:
    """Tests for request validation on the download_docx endpoint."""

    def test_returns_422_for_missing_draft_id(
        self,
        test_client: TestClient,
    ):
        """Test that the endpoint returns 422 when draft_id is missing."""
        response = test_client.post(
            "/api/v1/qgen/download_docx",
            json={
                "mode": "answer",
            },
        )
        assert response.status_code == 422

    def test_returns_404_for_nonexistent_draft(
        self,
        test_client: TestClient,
    ):
        """Test that the endpoint returns 404 for a non-existent draft."""
        response = test_client.post(
            "/api/v1/qgen/download_docx",
            json={
                "draft_id": str(uuid.uuid4()),
                "mode": "answer",
            },
        )
        assert response.status_code == 404


class TestDownloadDOCXFunctional:
    """Functional tests for the download_docx endpoint."""

    @pytest.mark.slow
    def test_generates_docx_with_questions_only(
        self,
        test_client: TestClient,
        test_draft_with_section: Dict[str, Any],
    ):
        """Test that the endpoint generates a DOCX with questions only."""
        response = test_client.post(
            "/api/v1/qgen/download_docx",
            json={
                "draft_id": test_draft_with_section["draft_id"],
                "mode": "paper",
            },
        )
        
        assert response.status_code == 200
        # DOCX responses should have appropriate content type
        content_type = response.headers.get("content-type", "")
        assert "application/vnd.openxmlformats-officedocument" in content_type or "application/octet-stream" in content_type

    @pytest.mark.slow
    def test_generates_docx_with_answers(
        self,
        test_client: TestClient,
        test_draft_with_section: Dict[str, Any],
    ):
        """Test that the endpoint generates a DOCX with answers included."""
        response = test_client.post(
            "/api/v1/qgen/download_docx",
            json={
                "draft_id": test_draft_with_section["draft_id"],
                "mode": "answer",
            },
        )
        
        assert response.status_code == 200

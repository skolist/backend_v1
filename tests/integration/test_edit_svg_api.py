"""
Integration tests for the edit_svg API endpoint.

Tests the AI-powered SVG editing functionality.
"""

import uuid
from typing import Any

import pytest
from fastapi.testclient import TestClient
from supabase import Client

from supabase_dir import (
    GenImagesInsert,
    GenQuestionsInsert,
    PublicHardnessLevelEnumEnum,
    PublicQuestionTypeEnumEnum,
)

# ============================================================================
# AUTH TESTS
# ============================================================================


class TestEditSVGAuth:
    """Tests for authentication on the edit_svg endpoint."""

    def test_returns_401_without_auth_token(
        self,
        unauthenticated_test_client: TestClient,
    ):
        """Test that the endpoint returns 401 when no auth token is provided."""
        response = unauthenticated_test_client.post(
            "/api/v1/qgen/edit_svg",
            data={
                "gen_image_id": str(uuid.uuid4()),
                "instruction": "Move the label to the left",
            },
        )
        assert response.status_code == 401


# ============================================================================
# VALIDATION TESTS
# ============================================================================


class TestEditSVGValidation:
    """Tests for request validation on the edit_svg endpoint."""

    def test_returns_422_for_missing_gen_image_id(
        self,
        test_client: TestClient,
    ):
        """Test that the endpoint returns 422 when gen_image_id is missing."""
        response = test_client.post(
            "/api/v1/qgen/edit_svg",
            data={
                "instruction": "Move the label to the left",
            },
        )
        assert response.status_code == 422

    def test_returns_422_for_missing_instruction(
        self,
        test_client: TestClient,
    ):
        """Test that the endpoint returns 422 when instruction is missing."""
        response = test_client.post(
            "/api/v1/qgen/edit_svg",
            data={
                "gen_image_id": str(uuid.uuid4()),
            },
        )
        assert response.status_code == 422


# ============================================================================
# FUNCTIONAL TESTS
# ============================================================================


class TestEditSVGFunctional:
    """Functional tests for the edit_svg endpoint."""

    @pytest.fixture
    def test_gen_image(
        self,
        service_supabase_client: Client,
        test_activity: dict[str, Any],
    ):
        """Create a test gen_image for SVG editing."""
        image_id = str(uuid.uuid4())
        question_id = str(uuid.uuid4())

        # Create a gen_question first (required for gen_image)
        question_data = GenQuestionsInsert(
            id=uuid.UUID(question_id),
            activity_id=uuid.UUID(test_activity["id"]),
            question_type=PublicQuestionTypeEnumEnum.MCQ4,
            question_text="Test question with image?",
            option1="Option A",
            option2="Option B",
            option3="Option C",
            option4="Option D",
            correct_mcq_option=1,
            answer_text="Option A",
            hardness_level=PublicHardnessLevelEnumEnum.EASY,
            marks=1,
        )
        service_supabase_client.table("gen_questions").insert(
            question_data.model_dump(mode="json", exclude_none=True)
        ).execute()

        # Create gen_image with SVG content
        sample_svg = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200">
            <circle cx="100" cy="100" r="50" fill="blue"/>
            <text x="100" y="100" text-anchor="middle">r = 50</text>
        </svg>"""

        image_data = GenImagesInsert(
            id=uuid.UUID(image_id),
            gen_question_id=uuid.UUID(question_id),
            svg_string=sample_svg,
            position=0,
        )
        service_supabase_client.table("gen_images").insert(
            image_data.model_dump(mode="json", exclude_none=True)
        ).execute()

        yield {
            "image_id": image_id,
            "question_id": question_id,
        }

        # Cleanup
        service_supabase_client.table("gen_images").delete().eq("id", image_id).execute()
        service_supabase_client.table("gen_questions").delete().eq("id", question_id).execute()

    def test_edits_svg_with_valid_instruction(
        self,
        test_client: TestClient,
        test_gen_image: dict[str, Any],
    ):
        """Test that the endpoint edits SVG with a valid instruction."""
        response = test_client.post(
            "/api/v1/qgen/edit_svg",
            data={
                "gen_image_id": test_gen_image["image_id"],
                "instruction": "Change the circle radius to 75",
            },
        )

        assert response.status_code == 200
        data = response.json()

        # Should return updated SVG
        assert "svg_string" in data or "id" in data

    def test_returns_400_for_nonexistent_image(
        self,
        test_client: TestClient,
    ):
        """Test that the endpoint returns 400/404 for non-existent image."""
        response = test_client.post(
            "/api/v1/qgen/edit_svg",
            data={
                "gen_image_id": str(uuid.uuid4()),
                "instruction": "Move the label",
            },
        )

        # Should return 400 or 404
        assert response.status_code in [400, 404]

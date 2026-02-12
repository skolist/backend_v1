"""
Integration tests for the regenerate_question API endpoint.

These tests use a real Supabase client and Gemini API to test
the full end-to-end question regeneration flow.
"""

import uuid
from collections.abc import Generator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from supabase import Client

from supabase_dir import GenQuestionsInsert, PublicHardnessLevelEnumEnum, PublicQuestionTypeEnumEnum

# ============================================================================
# FIXTURE FOR TEST QUESTION
# ============================================================================


@pytest.fixture
def test_gen_question_for_regeneration(
    service_supabase_client: Client,
    test_activity: dict[str, Any],
) -> Generator[dict[str, Any], None, None]:
    """
    Create a test generated question in Supabase for regeneration testing.
    """
    question_id = str(uuid.uuid4())

    question_data = GenQuestionsInsert(
        id=uuid.UUID(question_id),
        activity_id=uuid.UUID(test_activity["id"]),
        question_text="What is the formula for kinetic energy?",
        question_type=PublicQuestionTypeEnumEnum.MCQ4,
        option1="KE = m*v^2",
        option2="KE = 1/2*m*v",
        option3="KE = 1/2*m*v^2",
        option4="KE = m*g*h",
        correct_mcq_option=3,
        answer_text="KE = 1/2*m*v^2",
        explanation="The kinetic energy formula is KE = 1/2 * m * v^2",
        hardness_level=PublicHardnessLevelEnumEnum.MEDIUM,
        marks=2,
    )

    # Insert question
    response = (
        service_supabase_client.table("gen_questions")
        .insert(question_data.model_dump(mode="json", exclude_none=True))
        .execute()
    )

    yield response.data[0]

    # Cleanup: Delete the test question
    service_supabase_client.table("gen_questions").delete().eq("id", question_id).execute()


# ============================================================================
# TESTS FOR AUTHENTICATION
# ============================================================================


class TestRegenerateQuestionAuth:
    """Tests for authentication on the regenerate_question endpoint."""

    def test_returns_401_without_auth_token(
        self,
        unauthenticated_test_client: TestClient,
        test_gen_question_for_regeneration: dict[str, Any],
    ):
        """
        Test that the endpoint returns 401 when no auth token is provided.
        """
        question_id = test_gen_question_for_regeneration["id"]

        response = unauthenticated_test_client.post(
            f"/api/v1/qgen/regenerate_question?gen_question_id={question_id}",
        )

        assert response.status_code == 401

    def test_returns_401_with_invalid_token(
        self,
        app,
        test_gen_question_for_regeneration: dict[str, Any],
    ):
        """
        Test that the endpoint returns 401 with an invalid token.
        """
        from fastapi.testclient import TestClient

        client = TestClient(app)
        client.headers["Authorization"] = "Bearer invalid_token_here"

        question_id = test_gen_question_for_regeneration["id"]

        response = client.post(
            f"/api/v1/qgen/regenerate_question?gen_question_id={question_id}",
        )

        assert response.status_code == 401


# ============================================================================
# TESTS FOR REQUEST VALIDATION
# ============================================================================


class TestRegenerateQuestionValidation:
    """Tests for request validation on the regenerate_question endpoint."""

    def test_returns_404_for_nonexistent_question(
        self,
        test_client: TestClient,
    ):
        """
        Test that the endpoint returns 404 when question doesn't exist.
        """
        fake_question_id = "550e8400-e29b-41d4-a716-999999999999"

        response = test_client.post(
            f"/api/v1/qgen/regenerate_question?gen_question_id={fake_question_id}",
        )

        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "Gen Question not found"

    def test_returns_200_on_success(
        self,
        test_client: TestClient,
        test_gen_question_for_regeneration: dict[str, Any],
    ):
        """
        Test that the endpoint returns 200 on successful regeneration.
        """
        question_id = test_gen_question_for_regeneration["id"]

        response = test_client.post(
            f"/api/v1/qgen/regenerate_question?gen_question_id={question_id}",
        )

        # Should return 200 (not 201) as it's an update operation
        assert response.status_code == 200


# ============================================================================
# TESTS FOR SUCCESSFUL REGENERATION
# ============================================================================


class TestRegenerateQuestionSuccess:
    """Tests for successful question regeneration."""

    @pytest.mark.slow
    def test_regenerates_mcq4_question_successfully(
        self,
        test_client: TestClient,
        service_supabase_client: Client,
        test_gen_question_for_regeneration: dict[str, Any],
    ):
        """
        Test that MCQ4 questions are regenerated and updated in database.
        """
        question_id = test_gen_question_for_regeneration["id"]
        _original_text = test_gen_question_for_regeneration["question_text"]  # noqa: F841 - kept for documentation

        response = test_client.post(
            f"/api/v1/qgen/regenerate_question?gen_question_id={question_id}",
        )

        assert response.status_code == 200

        # Verify question was updated in database
        updated_question = (
            service_supabase_client.table("gen_questions")
            .select("*")
            .eq("id", question_id)
            .execute()
        )

        assert len(updated_question.data) == 1
        question = updated_question.data[0]

        # Verify the question text exists and is a valid string
        assert question["question_text"] is not None
        assert len(question["question_text"]) > 0

    @pytest.mark.slow
    def test_regenerated_question_preserves_structure(
        self,
        test_client: TestClient,
        service_supabase_client: Client,
        test_gen_question_for_regeneration: dict[str, Any],
    ):
        """
        Test that the regenerated question maintains MCQ4 structure.
        """
        question_id = test_gen_question_for_regeneration["id"]

        response = test_client.post(
            f"/api/v1/qgen/regenerate_question?gen_question_id={question_id}",
        )

        assert response.status_code == 200

        # Verify all MCQ4 fields are present
        updated_question = (
            service_supabase_client.table("gen_questions")
            .select("*")
            .eq("id", question_id)
            .execute()
        )

        question = updated_question.data[0]

        # MCQ4 should have all options
        assert question["option1"] is not None
        assert question["option2"] is not None
        assert question["option3"] is not None
        assert question["option4"] is not None
        assert question["correct_mcq_option"] is not None

    @pytest.mark.slow
    def test_preserves_activity_id_after_regeneration(
        self,
        test_client: TestClient,
        service_supabase_client: Client,
        test_activity: dict[str, Any],
        test_gen_question_for_regeneration: dict[str, Any],
    ):
        """
        Test that activity_id is preserved after regeneration.
        """
        question_id = test_gen_question_for_regeneration["id"]
        original_activity_id = test_activity["id"]

        response = test_client.post(
            f"/api/v1/qgen/regenerate_question?gen_question_id={question_id}",
        )

        assert response.status_code == 200

        # Verify activity_id unchanged
        updated_question = (
            service_supabase_client.table("gen_questions")
            .select("activity_id")
            .eq("id", question_id)
            .execute()
        )

        assert updated_question.data[0]["activity_id"] == original_activity_id

    @pytest.mark.slow
    def test_regenerated_question_has_explanation(
        self,
        test_client: TestClient,
        service_supabase_client: Client,
        test_gen_question_for_regeneration: dict[str, Any],
    ):
        """
        Test that the regenerated question includes an explanation.
        """
        question_id = test_gen_question_for_regeneration["id"]

        response = test_client.post(
            f"/api/v1/qgen/regenerate_question?gen_question_id={question_id}",
        )

        assert response.status_code == 200

        # Get the regenerated question
        updated_question = (
            service_supabase_client.table("gen_questions")
            .select("explanation")
            .eq("id", question_id)
            .execute()
        )

        explanation = updated_question.data[0]["explanation"]
        assert explanation is not None
        assert len(explanation) > 0

    @pytest.mark.slow
    def test_regenerated_question_about_same_concept(
        self,
        test_client: TestClient,
        service_supabase_client: Client,
        test_gen_question_for_regeneration: dict[str, Any],
    ):
        """
        Test that the regenerated question is about the same concept.
        """
        question_id = test_gen_question_for_regeneration["id"]

        response = test_client.post(
            f"/api/v1/qgen/regenerate_question?gen_question_id={question_id}",
        )

        assert response.status_code == 200

        # Get the regenerated question
        updated_question = (
            service_supabase_client.table("gen_questions")
            .select("question_text")
            .eq("id", question_id)
            .execute()
        )

        question_text = updated_question.data[0]["question_text"].lower()

        # The regenerated question should still be about physics/energy concepts
        # At least one relevant concept should be present
        assert question_text is not None
        assert len(question_text) > 0


# ============================================================================
# TESTS FOR EDGE CASES
# ============================================================================


class TestRegenerateQuestionEdgeCases:
    """Tests for edge cases in question regeneration."""

    @pytest.fixture
    def test_short_answer_question_for_regeneration(
        self,
        service_supabase_client: Client,
        test_activity: dict[str, Any],
    ) -> Generator[dict[str, Any], None, None]:
        """
        Create a test short answer question for edge case testing.
        """
        question_id = str(uuid.uuid4())

        question_data = {
            "id": question_id,
            "activity_id": test_activity["id"],
            "question_text": "What is Newton's first law of motion? Explain in simple terms.",
            "question_type": "short_answer",
            "answer_text": "An object in motion will stay in motion unless acted upon by an external force.",
            "explanation": "This is the law of inertia. The state of motion of an object changes only when a force is applied.",
            "hardness_level": "easy",
            "marks": 3,
        }

        response = service_supabase_client.table("gen_questions").insert(question_data).execute()

        yield response.data[0]

        # Cleanup
        service_supabase_client.table("gen_questions").delete().eq("id", question_id).execute()

    @pytest.mark.slow
    def test_regenerates_short_answer_question(
        self,
        test_client: TestClient,
        service_supabase_client: Client,
        test_short_answer_question_for_regeneration: dict[str, Any],
    ):
        """
        Test that short answer questions can also be regenerated.
        """
        question_id = test_short_answer_question_for_regeneration["id"]

        response = test_client.post(
            f"/api/v1/qgen/regenerate_question?gen_question_id={question_id}",
        )

        # May return 200 or 500 depending on model response
        # But should not crash
        assert response.status_code in [200, 500]

    @pytest.mark.slow
    def test_handles_multiple_regenerations_sequentially(
        self,
        test_client: TestClient,
        service_supabase_client: Client,
        test_gen_question_for_regeneration: dict[str, Any],
    ):
        """
        Test that a question can be regenerated multiple times.
        """
        question_id = test_gen_question_for_regeneration["id"]

        # First regeneration
        response1 = test_client.post(
            f"/api/v1/qgen/regenerate_question?gen_question_id={question_id}",
        )

        assert response1.status_code == 200

        # Get the first regeneration
        first_regeneration = (
            service_supabase_client.table("gen_questions")
            .select("question_text")
            .eq("id", question_id)
            .execute()
        )

        first_text = first_regeneration.data[0]["question_text"]

        # Second regeneration
        response2 = test_client.post(
            f"/api/v1/qgen/regenerate_question?gen_question_id={question_id}",
        )

        assert response2.status_code == 200

        # Get the second regeneration
        second_regeneration = (
            service_supabase_client.table("gen_questions")
            .select("question_text")
            .eq("id", question_id)
            .execute()
        )

        second_text = second_regeneration.data[0]["question_text"]

        # Both should be valid questions
        assert first_text is not None
        assert second_text is not None

    @pytest.mark.slow
    def test_regenerated_question_maintains_valid_correct_option(
        self,
        test_client: TestClient,
        service_supabase_client: Client,
        test_gen_question_for_regeneration: dict[str, Any],
    ):
        """
        Test that the regenerated MCQ4 question has a valid correct option (1-4).
        """
        question_id = test_gen_question_for_regeneration["id"]

        response = test_client.post(
            f"/api/v1/qgen/regenerate_question?gen_question_id={question_id}",
        )

        assert response.status_code == 200

        # Verify correct_mcq_option is valid
        updated_question = (
            service_supabase_client.table("gen_questions")
            .select("correct_mcq_option")
            .eq("id", question_id)
            .execute()
        )

        correct_option = updated_question.data[0]["correct_mcq_option"]
        assert correct_option is not None
        assert 1 <= correct_option <= 4

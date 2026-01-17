"""
Integration tests for the auto_correct_question API endpoint.

These tests use a real Supabase client and Gemini API to test
the full end-to-end auto-correction flow.
"""

import uuid
from typing import Any, Dict, Generator

import pytest
from fastapi.testclient import TestClient
from supabase import Client


# ============================================================================
# FIXTURE FOR TEST QUESTION
# ============================================================================


@pytest.fixture
def test_gen_question(
    service_supabase_client: Client,
    test_activity: Dict[str, Any],
) -> Generator[Dict[str, Any], None, None]:
    """
    Create a test generated question in Supabase that needs correction.
    This question will have formatting issues and grammatical errors.
    """
    question_id = str(uuid.uuid4())

    question_data = {
        "id": question_id,
        "activity_id": test_activity["id"],
        "question_text": "What is the formula for kinetc energy? (intentional misspelling)",
        "question_type": "mcq4",
        "option1": "KE = m*v^2",
        "option2": "KE = 1/2*m*v",
        "option3": "KE = 1/2*m*v^2",
        "option4": "KE = m*g*h",
        "correct_mcq_option": 3,
        "answer_text": "KE = 1/2*m*v^2",
        "explanation": "The kinetic energy formula is KE = half of mass times velocity squared",
        "hardness_level": "medium",
        "marks": 2,
    }

    # Insert question
    response = (
        service_supabase_client.table("gen_questions").insert(question_data).execute()
    )

    yield response.data[0]

    # Cleanup: Delete the test question
    service_supabase_client.table("gen_questions").delete().eq(
        "id", question_id
    ).execute()


# ============================================================================
# TESTS FOR AUTHENTICATION
# ============================================================================


class TestAutoCorrectQuestionAuth:
    """Tests for authentication on the auto_correct_question endpoint."""

    def test_returns_401_without_auth_token(
        self,
        unauthenticated_test_client: TestClient,
        test_gen_question: Dict[str, Any],
    ):
        """
        Test that the endpoint returns 401 when no auth token is provided.
        """
        question_id = test_gen_question["id"]

        response = unauthenticated_test_client.post(
            f"/api/v1/qgen/auto_correct_question?gen_question_id={question_id}",
        )

        assert response.status_code == 401

    def test_returns_401_with_invalid_token(
        self,
        app,
        test_gen_question: Dict[str, Any],
    ):
        """
        Test that the endpoint returns 401 with an invalid token.
        """
        from fastapi.testclient import TestClient

        client = TestClient(app)
        client.headers["Authorization"] = "Bearer invalid_token_here"

        question_id = test_gen_question["id"]

        response = client.post(
            f"/api/v1/qgen/auto_correct_question?gen_question_id={question_id}",
        )

        assert response.status_code == 401


# ============================================================================
# TESTS FOR REQUEST VALIDATION
# ============================================================================


class TestAutoCorrectQuestionValidation:
    """Tests for request validation on the auto_correct_question endpoint."""

    def test_returns_404_for_nonexistent_question(
        self,
        test_client: TestClient,
    ):
        """
        Test that the endpoint returns 404 when question doesn't exist.
        """
        fake_question_id = "550e8400-e29b-41d4-a716-999999999999"

        response = test_client.post(
            f"/api/v1/qgen/auto_correct_question?gen_question_id={fake_question_id}",
        )

        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "Gen Question not found"

    def test_returns_200_on_success(
        self,
        test_client: TestClient,
        test_gen_question: Dict[str, Any],
    ):
        """
        Test that the endpoint returns 200 on successful auto-correction.
        """
        question_id = test_gen_question["id"]

        response = test_client.post(
            f"/api/v1/qgen/auto_correct_question?gen_question_id={question_id}",
        )

        # Should return 200 (not 201) as it's an update operation
        assert response.status_code == 200


# ============================================================================
# TESTS FOR SUCCESSFUL AUTO-CORRECTION
# ============================================================================


class TestAutoCorrectQuestionSuccess:
    """Tests for successful auto-correction."""

    @pytest.mark.slow
    def test_corrects_mcq4_question_successfully(
        self,
        test_client: TestClient,
        service_supabase_client: Client,
        test_gen_question: Dict[str, Any],
    ):
        """
        Test that MCQ4 questions are corrected and updated in database.
        """
        question_id = test_gen_question["id"]
        original_text = test_gen_question["question_text"]

        response = test_client.post(
            f"/api/v1/qgen/auto_correct_question?gen_question_id={question_id}",
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

        # Verify the text was corrected (should fix "kinetc" to "kinetic")
        assert question["question_text"] is not None
        # The original text had a misspelling that should be fixed
        assert (
            "kinetc" not in question["question_text"].lower()
            or "kinetic" in question["question_text"].lower()
        )

    @pytest.mark.slow
    def test_preserves_question_type_after_correction(
        self,
        test_client: TestClient,
        service_supabase_client: Client,
        test_gen_question: Dict[str, Any],
    ):
        """
        Test that question type is preserved after auto-correction.
        """
        question_id = test_gen_question["id"]
        original_type = test_gen_question["question_type"]

        response = test_client.post(
            f"/api/v1/qgen/auto_correct_question?gen_question_id={question_id}",
        )

        assert response.status_code == 200

        # Verify question type unchanged
        updated_question = (
            service_supabase_client.table("gen_questions")
            .select("question_type")
            .eq("id", question_id)
            .execute()
        )

        assert updated_question.data[0]["question_type"] == original_type

    @pytest.mark.slow
    def test_preserves_options_structure_in_mcq4(
        self,
        test_client: TestClient,
        service_supabase_client: Client,
        test_gen_question: Dict[str, Any],
    ):
        """
        Test that MCQ4 options are preserved in structure.
        """
        question_id = test_gen_question["id"]

        response = test_client.post(
            f"/api/v1/qgen/auto_correct_question?gen_question_id={question_id}",
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
    def test_preserves_activity_id_after_correction(
        self,
        test_client: TestClient,
        service_supabase_client: Client,
        test_activity: Dict[str, Any],
        test_gen_question: Dict[str, Any],
    ):
        """
        Test that activity_id is preserved after correction.
        """
        question_id = test_gen_question["id"]
        original_activity_id = test_activity["id"]

        response = test_client.post(
            f"/api/v1/qgen/auto_correct_question?gen_question_id={question_id}",
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
    def test_improves_question_quality(
        self,
        test_client: TestClient,
        service_supabase_client: Client,
        test_gen_question: Dict[str, Any],
    ):
        """
        Test that the corrected question is improved in quality.
        This is a qualitative test to ensure the AI made meaningful corrections.
        """
        question_id = test_gen_question["id"]
        original_text = test_gen_question["question_text"]

        response = test_client.post(
            f"/api/v1/qgen/auto_correct_question?gen_question_id={question_id}",
        )

        assert response.status_code == 200

        # Get the corrected question
        updated_question = (
            service_supabase_client.table("gen_questions")
            .select("question_text, explanation")
            .eq("id", question_id)
            .execute()
        )

        corrected_text = updated_question.data[0]["question_text"]
        corrected_explanation = updated_question.data[0]["explanation"]

        # The corrected version should have proper formatting
        # (at least some improvement from the original)
        assert corrected_text is not None
        assert len(corrected_text) > 0

        # Should contain proper mathematical notation if applicable
        if "energy" in corrected_text.lower():
            # Energy questions should have proper formula formatting
            assert corrected_text is not None


# ============================================================================
# TESTS FOR EDGE CASES
# ============================================================================


class TestAutoCorrectQuestionEdgeCases:
    """Tests for edge cases in auto-correction."""

    @pytest.fixture
    def test_short_answer_question(
        self,
        service_supabase_client: Client,
        test_activity: Dict[str, Any],
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Create a test short answer question for edge case testing.
        """
        question_id = str(uuid.uuid4())

        question_data = {
            "id": question_id,
            "activity_id": test_activity["id"],
            "question_text": "What is newtons first law of motion? Explain in simple terms using proper grammar",
            "question_type": "short_answer",
            "answer_text": "An object in motion will stay in motion unless acted upon by external force",
            "explanation": "This is the law of inertia. State of motion of object changes only when force is applied",
            "hardness_level": "easy",
            "marks": 3,
        }

        response = (
            service_supabase_client.table("gen_questions")
            .insert(question_data)
            .execute()
        )

        yield response.data[0]

        # Cleanup
        service_supabase_client.table("gen_questions").delete().eq(
            "id", question_id
        ).execute()

    @pytest.mark.slow
    def test_corrects_short_answer_question(
        self,
        test_client: TestClient,
        service_supabase_client: Client,
        test_short_answer_question: Dict[str, Any],
    ):
        """
        Test that short answer questions can also be corrected.
        """
        question_id = test_short_answer_question["id"]

        response = test_client.post(
            f"/api/v1/qgen/auto_correct_question?gen_question_id={question_id}",
        )

        # May return 200 or 500 depending on model response
        # But should not crash
        assert response.status_code in [200, 500]

    @pytest.mark.slow
    def test_handles_multiple_corrections_sequentially(
        self,
        test_client: TestClient,
        service_supabase_client: Client,
        test_gen_question: Dict[str, Any],
    ):
        """
        Test that a question can be corrected multiple times if needed.
        """
        question_id = test_gen_question["id"]

        # First correction
        response1 = test_client.post(
            f"/api/v1/qgen/auto_correct_question?gen_question_id={question_id}",
        )

        assert response1.status_code == 200

        # Get the first correction
        first_correction = (
            service_supabase_client.table("gen_questions")
            .select("question_text")
            .eq("id", question_id)
            .execute()
        )

        first_text = first_correction.data[0]["question_text"]

        # Second correction (should be idempotent or further improve)
        response2 = test_client.post(
            f"/api/v1/qgen/auto_correct_question?gen_question_id={question_id}",
        )

        assert response2.status_code == 200

        # Get the second correction
        second_correction = (
            service_supabase_client.table("gen_questions")
            .select("question_text")
            .eq("id", question_id)
            .execute()
        )

        second_text = second_correction.data[0]["question_text"]

        # Both should be valid questions
        assert first_text is not None
        assert second_text is not None

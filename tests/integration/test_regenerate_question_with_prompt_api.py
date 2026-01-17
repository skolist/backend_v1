"""
Integration tests for the regenerate_question_with_prompt API endpoint.

These tests use a real Supabase client and Gemini API to test
the full end-to-end question regeneration with custom prompts flow.
"""

import io
import uuid
from typing import Any, Dict, Generator

import pytest
from fastapi.testclient import TestClient
from supabase import Client


# ============================================================================
# FIXTURE FOR TEST QUESTION
# ============================================================================


@pytest.fixture
def test_gen_question_for_prompt_regeneration(
    service_supabase_client: Client,
    test_activity: Dict[str, Any],
) -> Generator[Dict[str, Any], None, None]:
    """
    Create a test generated question in Supabase for prompt-based regeneration testing.
    """
    question_id = str(uuid.uuid4())

    question_data = {
        "id": question_id,
        "activity_id": test_activity["id"],
        "question_text": "What is the speed of light in a vacuum?",
        "question_type": "mcq4",
        "option1": "3 x 10^6 m/s",
        "option2": "3 x 10^7 m/s",
        "option3": "3 x 10^8 m/s",
        "option4": "3 x 10^9 m/s",
        "correct_mcq_option": 3,
        "answer_text": "3 x 10^8 m/s",
        "explanation": "The speed of light in a vacuum is approximately 3 x 10^8 meters per second.",
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


class TestRegenerateQuestionWithPromptAuth:
    """Tests for authentication on the regenerate_question_with_prompt endpoint."""

    def test_returns_401_without_auth_token(
        self,
        unauthenticated_test_client: TestClient,
        test_gen_question_for_prompt_regeneration: Dict[str, Any],
    ):
        """
        Test that the endpoint returns 401 when no auth token is provided.
        """
        question_id = test_gen_question_for_prompt_regeneration["id"]

        response = unauthenticated_test_client.post(
            "/api/v1/qgen/regenerate_question_with_prompt",
            data={"gen_question_id": question_id},
        )

        assert response.status_code == 401

    def test_returns_401_with_invalid_token(
        self,
        app,
        test_gen_question_for_prompt_regeneration: Dict[str, Any],
    ):
        """
        Test that the endpoint returns 401 with an invalid token.
        """
        from fastapi.testclient import TestClient

        client = TestClient(app)
        client.headers["Authorization"] = "Bearer invalid_token_here"

        question_id = test_gen_question_for_prompt_regeneration["id"]

        response = client.post(
            "/api/v1/qgen/regenerate_question_with_prompt",
            data={"gen_question_id": question_id},
        )

        assert response.status_code == 401


# ============================================================================
# TESTS FOR REQUEST VALIDATION
# ============================================================================


class TestRegenerateQuestionWithPromptValidation:
    """Tests for request validation on the regenerate_question_with_prompt endpoint."""

    def test_returns_404_for_nonexistent_question(
        self,
        test_client: TestClient,
    ):
        """
        Test that the endpoint returns 404 when question doesn't exist.
        """
        fake_question_id = "550e8400-e29b-41d4-a716-999999999999"

        response = test_client.post(
            "/api/v1/qgen/regenerate_question_with_prompt",
            data={"gen_question_id": fake_question_id},
        )

        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "Gen Question not found"

    def test_returns_200_on_success_without_prompt(
        self,
        test_client: TestClient,
        test_gen_question_for_prompt_regeneration: Dict[str, Any],
    ):
        """
        Test that the endpoint returns 200 on successful regeneration without prompt.
        """
        question_id = test_gen_question_for_prompt_regeneration["id"]

        response = test_client.post(
            "/api/v1/qgen/regenerate_question_with_prompt",
            data={"gen_question_id": question_id},
        )

        assert response.status_code == 200

    def test_returns_200_on_success_with_prompt(
        self,
        test_client: TestClient,
        test_gen_question_for_prompt_regeneration: Dict[str, Any],
    ):
        """
        Test that the endpoint returns 200 on successful regeneration with prompt.
        """
        question_id = test_gen_question_for_prompt_regeneration["id"]

        response = test_client.post(
            "/api/v1/qgen/regenerate_question_with_prompt",
            data={
                "gen_question_id": question_id,
                "prompt": "Make this question slightly harder",
            },
        )

        assert response.status_code == 200


# ============================================================================
# TESTS FOR SUCCESSFUL REGENERATION WITH PROMPT
# ============================================================================


class TestRegenerateQuestionWithPromptSuccess:
    """Tests for successful question regeneration with custom prompts."""

    @pytest.mark.slow
    def test_regenerates_question_with_custom_prompt(
        self,
        test_client: TestClient,
        service_supabase_client: Client,
        test_gen_question_for_prompt_regeneration: Dict[str, Any],
    ):
        """
        Test that questions are regenerated with custom prompt and updated in database.
        """
        question_id = test_gen_question_for_prompt_regeneration["id"]

        response = test_client.post(
            "/api/v1/qgen/regenerate_question_with_prompt",
            data={
                "gen_question_id": question_id,
                "prompt": "Change the question to be about sound waves instead of light",
            },
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
    def test_regenerates_without_prompt_uses_same_concepts(
        self,
        test_client: TestClient,
        service_supabase_client: Client,
        test_gen_question_for_prompt_regeneration: Dict[str, Any],
    ):
        """
        Test that regeneration without prompt uses same concepts (default behavior).
        """
        question_id = test_gen_question_for_prompt_regeneration["id"]

        response = test_client.post(
            "/api/v1/qgen/regenerate_question_with_prompt",
            data={"gen_question_id": question_id},
        )

        assert response.status_code == 200

        # Verify question was updated
        updated_question = (
            service_supabase_client.table("gen_questions")
            .select("*")
            .eq("id", question_id)
            .execute()
        )

        question = updated_question.data[0]
        assert question["question_text"] is not None

    @pytest.mark.slow
    def test_regenerated_question_preserves_structure(
        self,
        test_client: TestClient,
        service_supabase_client: Client,
        test_gen_question_for_prompt_regeneration: Dict[str, Any],
    ):
        """
        Test that the regenerated question maintains MCQ4 structure.
        """
        question_id = test_gen_question_for_prompt_regeneration["id"]

        response = test_client.post(
            "/api/v1/qgen/regenerate_question_with_prompt",
            data={
                "gen_question_id": question_id,
                "prompt": "Keep the same structure but ask about a different physics constant",
            },
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
    def test_regenerated_question_has_explanation(
        self,
        test_client: TestClient,
        service_supabase_client: Client,
        test_gen_question_for_prompt_regeneration: Dict[str, Any],
    ):
        """
        Test that the regenerated question includes an explanation.
        """
        question_id = test_gen_question_for_prompt_regeneration["id"]

        response = test_client.post(
            "/api/v1/qgen/regenerate_question_with_prompt",
            data={
                "gen_question_id": question_id,
                "prompt": "Include a detailed explanation",
            },
        )

        assert response.status_code == 200

        updated_question = (
            service_supabase_client.table("gen_questions")
            .select("*")
            .eq("id", question_id)
            .execute()
        )

        question = updated_question.data[0]
        assert question["explanation"] is not None


# ============================================================================
# TESTS FOR FILE UPLOADS
# ============================================================================


class TestRegenerateQuestionWithFiles:
    """Tests for question regeneration with file attachments."""

    @pytest.mark.slow
    def test_regenerates_with_text_file(
        self,
        test_client: TestClient,
        service_supabase_client: Client,
        test_gen_question_for_prompt_regeneration: Dict[str, Any],
    ):
        """
        Test that questions can be regenerated with a text file attachment.
        """
        question_id = test_gen_question_for_prompt_regeneration["id"]

        # Create a simple text file
        text_content = b"The gravitational constant G = 6.674 x 10^-11 N(m/kg)^2"
        text_file = io.BytesIO(text_content)

        response = test_client.post(
            "/api/v1/qgen/regenerate_question_with_prompt",
            data={
                "gen_question_id": question_id,
                "prompt": "Use the information in the attached file to create a related question",
            },
            files=[("files", ("physics_constants.txt", text_file, "text/plain"))],
        )

        assert response.status_code == 200

    @pytest.mark.slow
    def test_regenerates_with_multiple_files(
        self,
        test_client: TestClient,
        test_gen_question_for_prompt_regeneration: Dict[str, Any],
    ):
        """
        Test that questions can be regenerated with multiple file attachments.
        """
        question_id = test_gen_question_for_prompt_regeneration["id"]

        # Create multiple text files
        file1_content = b"Speed of light: 3 x 10^8 m/s"
        file2_content = b"Speed of sound: 343 m/s"

        file1 = io.BytesIO(file1_content)
        file2 = io.BytesIO(file2_content)

        response = test_client.post(
            "/api/v1/qgen/regenerate_question_with_prompt",
            data={
                "gen_question_id": question_id,
                "prompt": "Create a comparison question using data from both files",
            },
            files=[
                ("files", ("light.txt", file1, "text/plain")),
                ("files", ("sound.txt", file2, "text/plain")),
            ],
        )

        assert response.status_code == 200

    @pytest.mark.slow
    def test_regenerates_with_files_but_no_prompt(
        self,
        test_client: TestClient,
        test_gen_question_for_prompt_regeneration: Dict[str, Any],
    ):
        """
        Test that questions can be regenerated with files but no custom prompt.
        """
        question_id = test_gen_question_for_prompt_regeneration["id"]

        text_content = b"Additional context for the question"
        text_file = io.BytesIO(text_content)

        response = test_client.post(
            "/api/v1/qgen/regenerate_question_with_prompt",
            data={"gen_question_id": question_id},
            files=[("files", ("context.txt", text_file, "text/plain"))],
        )

        assert response.status_code == 200


# ============================================================================
# TESTS FOR EDGE CASES
# ============================================================================


class TestRegenerateQuestionWithPromptEdgeCases:
    """Tests for edge cases in question regeneration with prompts."""

    @pytest.fixture
    def test_short_answer_question_for_prompt_regeneration(
        self,
        service_supabase_client: Client,
        test_activity: Dict[str, Any],
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Create a test short answer question for prompt-based regeneration testing.
        """
        question_id = str(uuid.uuid4())

        question_data = {
            "id": question_id,
            "activity_id": test_activity["id"],
            "question_text": "Explain the concept of inertia in your own words.",
            "question_type": "short_answer",
            "answer_text": "Inertia is the tendency of an object to resist changes in its state of motion.",
            "explanation": "Objects at rest stay at rest, objects in motion stay in motion unless acted upon by a force.",
            "hardness_level": "easy",
            "marks": 3,
        }

        response = (
            service_supabase_client.table("gen_questions")
            .insert(question_data)
            .execute()
        )

        yield response.data[0]

        service_supabase_client.table("gen_questions").delete().eq(
            "id", question_id
        ).execute()

    @pytest.mark.slow
    def test_regenerates_short_answer_with_prompt(
        self,
        test_client: TestClient,
        service_supabase_client: Client,
        test_short_answer_question_for_prompt_regeneration: Dict[str, Any],
    ):
        """
        Test that short answer questions can be regenerated with prompts.
        """
        question_id = test_short_answer_question_for_prompt_regeneration["id"]

        response = test_client.post(
            "/api/v1/qgen/regenerate_question_with_prompt",
            data={
                "gen_question_id": question_id,
                "prompt": "Ask about momentum instead of inertia",
            },
        )

        assert response.status_code == 200

        updated_question = (
            service_supabase_client.table("gen_questions")
            .select("*")
            .eq("id", question_id)
            .execute()
        )

        assert len(updated_question.data) == 1

    @pytest.mark.slow
    def test_handles_empty_prompt_string(
        self,
        test_client: TestClient,
        test_gen_question_for_prompt_regeneration: Dict[str, Any],
    ):
        """
        Test that empty prompt string falls back to default regeneration.
        """
        question_id = test_gen_question_for_prompt_regeneration["id"]

        response = test_client.post(
            "/api/v1/qgen/regenerate_question_with_prompt",
            data={
                "gen_question_id": question_id,
                "prompt": "",
            },
        )

        assert response.status_code == 200

    @pytest.mark.slow
    def test_handles_whitespace_only_prompt(
        self,
        test_client: TestClient,
        test_gen_question_for_prompt_regeneration: Dict[str, Any],
    ):
        """
        Test that whitespace-only prompt falls back to default regeneration.
        """
        question_id = test_gen_question_for_prompt_regeneration["id"]

        response = test_client.post(
            "/api/v1/qgen/regenerate_question_with_prompt",
            data={
                "gen_question_id": question_id,
                "prompt": "   ",
            },
        )

        assert response.status_code == 200

    @pytest.mark.slow
    def test_handles_very_long_prompt(
        self,
        test_client: TestClient,
        test_gen_question_for_prompt_regeneration: Dict[str, Any],
    ):
        """
        Test that the endpoint handles very long prompts.
        """
        question_id = test_gen_question_for_prompt_regeneration["id"]

        # Create a long but reasonable prompt
        long_prompt = "Make this question harder. " * 50

        response = test_client.post(
            "/api/v1/qgen/regenerate_question_with_prompt",
            data={
                "gen_question_id": question_id,
                "prompt": long_prompt,
            },
        )

        assert response.status_code == 200

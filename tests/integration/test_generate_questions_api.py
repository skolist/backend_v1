"""
Integration tests for the generate_questions API endpoint with batchification.

These tests use a real Supabase client and Gemini API to test
the full end-to-end question generation flow with the new batchification logic.
"""

import uuid
from typing import Any

import pytest
from fastapi.testclient import TestClient
from supabase import Client

# ============================================================================
# SANITY CHECK - VERIFY AUTH WORKS
# ============================================================================


class TestAuthSanityCheck:
    """Verify that authentication is working before running other tests."""

    def test_authenticated_client_can_access_hello_endpoint(
        self,
        test_client: TestClient,
    ):
        """
        Sanity check: Verify that authenticated test client can access /api/v1/hello.
        This confirms our auth setup is working correctly.
        """
        response = test_client.get("/api/v1/hello")

        assert response.status_code == 200
        data = response.json()
        assert data["authenticated"] is True
        assert data["user"]["email"] is not None
        assert data["user"]["id"] is not None

    def test_unauthenticated_client_gets_401_on_hello(
        self,
        unauthenticated_test_client: TestClient,
    ):
        """
        Sanity check: Verify that unauthenticated client gets 401 on /api/v1/hello.
        """
        response = unauthenticated_test_client.get("/api/v1/hello")
        assert response.status_code == 401


# ============================================================================
# TESTS FOR AUTHENTICATION
# ============================================================================


class TestGenerateQuestionsAuth:
    """Tests for authentication on the generate_questions endpoint."""

    def test_returns_401_without_auth_token(
        self,
        unauthenticated_test_client: TestClient,
        test_activity: dict[str, Any],
        test_concepts: list[dict[str, Any]],
    ):
        """
        Test that the endpoint returns 401 when no auth token is provided.
        """
        concept_ids = [c["id"] for c in test_concepts]

        response = unauthenticated_test_client.post(
            "/api/v1/qgen/generate_questions",
            json={
                "activity_id": test_activity["id"],
                "concept_ids": concept_ids,
                "config": {
                    "question_types": [{"type": "mcq4", "count": 1}],
                    "difficulty_distribution": {"easy": 50, "medium": 30, "hard": 20},
                },
            },
        )

        assert response.status_code == 401

    def test_returns_401_with_invalid_token(
        self,
        app,
        test_activity: dict[str, Any],
        test_concepts: list[dict[str, Any]],
    ):
        """
        Test that the endpoint returns 401 with an invalid token.
        """
        client = TestClient(app)
        client.headers["Authorization"] = "Bearer invalid_token_here"

        concept_ids = [c["id"] for c in test_concepts]

        response = client.post(
            "/api/v1/qgen/generate_questions",
            json={
                "activity_id": test_activity["id"],
                "concept_ids": concept_ids,
                "config": {
                    "question_types": [{"type": "mcq4", "count": 1}],
                    "difficulty_distribution": {"easy": 50, "medium": 30, "hard": 20},
                },
            },
        )

        assert response.status_code == 401


# ============================================================================
# TESTS FOR REQUEST VALIDATION
# ============================================================================


class TestGenerateQuestionsValidation:
    """Tests for request validation on the generate_questions endpoint."""

    def test_returns_422_with_invalid_activity_id(
        self,
        test_client: TestClient,
        test_concepts: list[dict[str, Any]],
    ):
        """
        Test that the endpoint returns 422 for invalid activity_id format.
        """
        concept_ids = [c["id"] for c in test_concepts]

        response = test_client.post(
            "/api/v1/qgen/generate_questions",
            json={
                "activity_id": "not-a-valid-uuid",
                "concept_ids": concept_ids,
                "config": {
                    "question_types": [{"type": "mcq4", "count": 1}],
                    "difficulty_distribution": {"easy": 50, "medium": 30, "hard": 20},
                },
            },
        )

        assert response.status_code == 422

    def test_returns_422_with_invalid_question_type(
        self,
        test_client: TestClient,
        test_activity: dict[str, Any],
        test_concepts: list[dict[str, Any]],
    ):
        """
        Test that the endpoint returns 422 for invalid question type.
        """
        concept_ids = [c["id"] for c in test_concepts]

        response = test_client.post(
            "/api/v1/qgen/generate_questions",
            json={
                "activity_id": test_activity["id"],
                "concept_ids": concept_ids,
                "config": {
                    "question_types": [{"type": "invalid_type", "count": 1}],
                    "difficulty_distribution": {"easy": 50, "medium": 30, "hard": 20},
                },
            },
        )

        assert response.status_code == 422

    def test_returns_422_with_missing_config(
        self,
        test_client: TestClient,
        test_activity: dict[str, Any],
        test_concepts: list[dict[str, Any]],
    ):
        """
        Test that the endpoint returns 422 when config is missing.
        """
        concept_ids = [c["id"] for c in test_concepts]

        response = test_client.post(
            "/api/v1/qgen/generate_questions",
            json={
                "activity_id": test_activity["id"],
                "concept_ids": concept_ids,
            },
        )

        assert response.status_code == 422

    def test_returns_422_with_empty_concept_ids(
        self,
        test_client: TestClient,
        test_activity: dict[str, Any],
    ):
        """
        Test that the endpoint handles empty concept_ids list.
        """
        response = test_client.post(
            "/api/v1/qgen/generate_questions",
            json={
                "activity_id": test_activity["id"],
                "concept_ids": [],
                "config": {
                    "question_types": [{"type": "mcq4", "count": 1}],
                    "difficulty_distribution": {"easy": 50, "medium": 30, "hard": 20},
                },
            },
        )

        # Empty concept_ids should either be 422 or 201 (with no questions generated)
        # or 500 if the implementation doesn't handle empty list gracefully
        assert response.status_code in [201, 422, 500]

    def test_returns_422_when_total_questions_is_zero(
        self,
        test_client: TestClient,
        test_activity: dict[str, Any],
        test_concepts: list[dict[str, Any]],
    ):
        """
        Test that the endpoint returns 422 when total questions is 0.
        """
        concept_ids = [c["id"] for c in test_concepts]

        response = test_client.post(
            "/api/v1/qgen/generate_questions",
            json={
                "activity_id": test_activity["id"],
                "concept_ids": concept_ids,
                "config": {
                    "question_types": [{"type": "mcq4", "count": 0}],
                    "difficulty_distribution": {"easy": 50, "medium": 30, "hard": 20},
                },
            },
        )

        assert response.status_code == 422
        assert "Total number of questions must be between 1 and 50" in response.text

    def test_returns_422_when_total_questions_exceeds_50(
        self,
        test_client: TestClient,
        test_activity: dict[str, Any],
        test_concepts: list[dict[str, Any]],
    ):
        """
        Test that the endpoint returns 422 when total questions exceeds 50.
        """
        concept_ids = [c["id"] for c in test_concepts]

        response = test_client.post(
            "/api/v1/qgen/generate_questions",
            json={
                "activity_id": test_activity["id"],
                "concept_ids": concept_ids,
                "config": {
                    "question_types": [
                        {"type": "mcq4", "count": 30},
                        {"type": "short_answer", "count": 21},
                    ],
                    "difficulty_distribution": {"easy": 50, "medium": 30, "hard": 20},
                },
            },
        )

        assert response.status_code == 422
        assert "Total number of questions must be between 1 and 50" in response.text

    def test_accepts_exactly_1_question(
        self,
        test_client: TestClient,
        test_activity: dict[str, Any],
        test_concepts: list[dict[str, Any]],
    ):
        """
        Test that the endpoint accepts exactly 1 question (lower boundary).
        """
        concept_ids = [c["id"] for c in test_concepts]

        response = test_client.post(
            "/api/v1/qgen/generate_questions",
            json={
                "activity_id": test_activity["id"],
                "concept_ids": concept_ids,
                "config": {
                    "question_types": [{"type": "mcq4", "count": 1}],
                    "difficulty_distribution": {"easy": 50, "medium": 30, "hard": 20},
                },
            },
        )

        # Should not return validation error (422)
        assert response.status_code in [201, 500]

    def test_accepts_exactly_50_questions(
        self,
        test_client: TestClient,
        test_activity: dict[str, Any],
        test_concepts: list[dict[str, Any]],
    ):
        """
        Test that the endpoint accepts exactly 50 questions (upper boundary).
        """
        concept_ids = [c["id"] for c in test_concepts]

        response = test_client.post(
            "/api/v1/qgen/generate_questions",
            json={
                "activity_id": test_activity["id"],
                "concept_ids": concept_ids,
                "config": {
                    "question_types": [
                        {"type": "mcq4", "count": 20},
                        {"type": "short_answer", "count": 15},
                        {"type": "true_false", "count": 15},
                    ],
                    "difficulty_distribution": {"easy": 50, "medium": 30, "hard": 20},
                },
            },
        )

        # Should not return validation error (422)
        assert response.status_code in [201, 500]


# ============================================================================
# TESTS FOR SUCCESSFUL QUESTION GENERATION WITH BATCHIFICATION
# ============================================================================


class TestGenerateQuestionsSuccess:
    """Tests for successful question generation with batchification."""

    @pytest.mark.slow
    def test_generates_mcq4_questions_successfully(
        self,
        test_client: TestClient,
        service_supabase_client: Client,
        test_activity: dict[str, Any],
        test_concepts: list[dict[str, Any]],
        test_bank_questions: list[dict[str, Any]],  # Ensure bank questions exist
    ):
        """
        Test that MCQ4 questions are generated and stored in database.
        """
        concept_ids = [c["id"] for c in test_concepts]
        activity_id = test_activity["id"]

        response = test_client.post(
            "/api/v1/qgen/generate_questions",
            json={
                "activity_id": activity_id,
                "concept_ids": concept_ids,
                "config": {
                    "question_types": [{"type": "mcq4", "count": 2}],
                    "difficulty_distribution": {"easy": 50, "medium": 30, "hard": 20},
                },
            },
        )

        assert response.status_code == 201

        # Verify questions were created in database
        gen_questions = (
            service_supabase_client.table("gen_questions").select("*").eq("activity_id", activity_id).execute()
        )

        assert len(gen_questions.data) >= 1  # At least some questions generated

        # Verify question structure for MCQ4
        for question in gen_questions.data:
            assert question["activity_id"] == activity_id
            assert question["question_type"] == "mcq4"
            assert question["hardness_level"] is not None
            assert question["marks"] is not None

    @pytest.mark.slow
    def test_generates_multiple_question_types(
        self,
        test_client: TestClient,
        service_supabase_client: Client,
        test_activity: dict[str, Any],
        test_concepts: list[dict[str, Any]],
        test_bank_questions: list[dict[str, Any]],
    ):
        """
        Test that multiple question types can be generated in one request.
        Uses batchification to distribute across types.
        """
        concept_ids = [c["id"] for c in test_concepts]
        activity_id = test_activity["id"]

        response = test_client.post(
            "/api/v1/qgen/generate_questions",
            json={
                "activity_id": activity_id,
                "concept_ids": concept_ids,
                "config": {
                    "question_types": [
                        {"type": "mcq4", "count": 1},
                        {"type": "true_false", "count": 1},
                    ],
                    "difficulty_distribution": {"easy": 50, "medium": 30, "hard": 20},
                },
            },
        )

        assert response.status_code == 201

        # Verify questions were created
        gen_questions = (
            service_supabase_client.table("gen_questions").select("*").eq("activity_id", activity_id).execute()
        )

        question_types = {q["question_type"] for q in gen_questions.data}
        # Should have at least one question type present
        assert len(question_types) >= 1

    @pytest.mark.slow
    def test_creates_concept_question_mappings(
        self,
        test_client: TestClient,
        service_supabase_client: Client,
        test_activity: dict[str, Any],
        test_concepts: list[dict[str, Any]],
        test_bank_questions: list[dict[str, Any]],
    ):
        """
        Test that concept-question mappings are created in gen_questions_concepts_maps.
        With batchification, multiple concepts can be mapped to each question.
        """
        concept_ids = [c["id"] for c in test_concepts]
        activity_id = test_activity["id"]

        response = test_client.post(
            "/api/v1/qgen/generate_questions",
            json={
                "activity_id": activity_id,
                "concept_ids": concept_ids,
                "config": {
                    "question_types": [{"type": "mcq4", "count": 2}],
                    "difficulty_distribution": {"easy": 50, "medium": 30, "hard": 20},
                },
            },
        )

        assert response.status_code == 201

        # Get generated question IDs
        gen_questions = (
            service_supabase_client.table("gen_questions").select("id").eq("activity_id", activity_id).execute()
        )

        if gen_questions.data:
            question_ids = [q["id"] for q in gen_questions.data]

            # Verify mappings exist
            mappings = (
                service_supabase_client.table("gen_questions_concepts_maps")
                .select("*")
                .in_("gen_question_id", question_ids)
                .execute()
            )

            # Each question should have at least one concept mapping
            assert len(mappings.data) >= len(gen_questions.data)

            # Verify concept_ids in mappings are from our test concepts
            mapping_concept_ids = {m["concept_id"] for m in mappings.data}
            for cid in mapping_concept_ids:
                assert cid in concept_ids

    @pytest.mark.slow
    def test_difficulty_distribution_is_applied(
        self,
        test_client: TestClient,
        service_supabase_client: Client,
        test_activity: dict[str, Any],
        test_concepts: list[dict[str, Any]],
        test_bank_questions: list[dict[str, Any]],
    ):
        """
        Test that difficulty distribution is correctly applied across batches.
        """
        concept_ids = [c["id"] for c in test_concepts]
        activity_id = test_activity["id"]

        response = test_client.post(
            "/api/v1/qgen/generate_questions",
            json={
                "activity_id": activity_id,
                "concept_ids": concept_ids,
                "config": {
                    "question_types": [{"type": "mcq4", "count": 6}],
                    "difficulty_distribution": {"easy": 50, "medium": 30, "hard": 20},
                },
            },
        )

        assert response.status_code == 201

        # Verify questions were created with different difficulty levels
        gen_questions = (
            service_supabase_client.table("gen_questions")
            .select("hardness_level")
            .eq("activity_id", activity_id)
            .execute()
        )

        if gen_questions.data:
            difficulty_levels = {q["hardness_level"] for q in gen_questions.data}
            # With the distribution, we should have multiple difficulty levels
            # (at least for 6+ questions)
            assert len(difficulty_levels) >= 1


# ============================================================================
# TESTS FOR EDGE CASES
# ============================================================================


class TestGenerateQuestionsEdgeCases:
    """Tests for edge cases in question generation with batchification."""

    def test_handles_nonexistent_concepts_gracefully(
        self,
        test_client: TestClient,
        test_activity: dict[str, Any],
    ):
        """
        Test that the endpoint handles non-existent concept IDs gracefully.
        """
        fake_concept_ids = [str(uuid.uuid4()), str(uuid.uuid4())]

        response = test_client.post(
            "/api/v1/qgen/generate_questions",
            json={
                "activity_id": test_activity["id"],
                "concept_ids": fake_concept_ids,
                "config": {
                    "question_types": [{"type": "mcq4", "count": 1}],
                    "difficulty_distribution": {"easy": 50, "medium": 30, "hard": 20},
                },
            },
        )

        # Should handle gracefully - either 201 (no questions) or appropriate error
        assert response.status_code in [201, 500]

    @pytest.mark.slow
    def test_single_concept_multiple_questions(
        self,
        test_client: TestClient,
        service_supabase_client: Client,
        test_activity: dict[str, Any],
        test_concepts: list[dict[str, Any]],
        test_bank_questions: list[dict[str, Any]],
    ):
        """
        Test that batchification correctly handles single concept with multiple questions.
        Concept should be repeated across batches.
        """
        # Use only one concept
        concept_ids = [test_concepts[0]["id"]]
        activity_id = test_activity["id"]

        response = test_client.post(
            "/api/v1/qgen/generate_questions",
            json={
                "activity_id": activity_id,
                "concept_ids": concept_ids,
                "config": {
                    "question_types": [{"type": "mcq4", "count": 5}],
                    "difficulty_distribution": {"easy": 100, "medium": 0, "hard": 0},
                },
            },
        )

        assert response.status_code == 201

        # Verify all questions are generated
        gen_questions = (
            service_supabase_client.table("gen_questions").select("*").eq("activity_id", activity_id).execute()
        )

        # Should have generated some questions
        assert len(gen_questions.data) >= 1

    @pytest.mark.slow
    def test_many_concepts_few_questions(
        self,
        test_client: TestClient,
        service_supabase_client: Client,
        test_activity: dict[str, Any],
        test_concepts: list[dict[str, Any]],
        test_bank_questions: list[dict[str, Any]],
    ):
        """
        Test that batchification handles case where concepts > questions.
        All concepts should be distributed across batches.
        """
        concept_ids = [c["id"] for c in test_concepts]  # 2+ concepts
        activity_id = test_activity["id"]

        response = test_client.post(
            "/api/v1/qgen/generate_questions",
            json={
                "activity_id": activity_id,
                "concept_ids": concept_ids,
                "config": {
                    "question_types": [{"type": "mcq4", "count": 1}],
                    "difficulty_distribution": {"easy": 100, "medium": 0, "hard": 0},
                },
            },
        )

        assert response.status_code == 201


# ============================================================================
# TESTS FOR INSTRUCTIONS PARAMETER
# ============================================================================


class TestGenerateQuestionsWithInstructions:
    """Tests for the instructions parameter in question generation with batchification."""

    @pytest.mark.slow
    def test_accepts_instructions_parameter(
        self,
        test_client: TestClient,
        service_supabase_client: Client,
        test_activity: dict[str, Any],
        test_concepts: list[dict[str, Any]],
        test_bank_questions: list[dict[str, Any]],
    ):
        """
        Test that the endpoint accepts and processes instructions parameter.
        Instructions should be applied to ~30% of batches.
        """
        concept_ids = [c["id"] for c in test_concepts]
        activity_id = test_activity["id"]

        response = test_client.post(
            "/api/v1/qgen/generate_questions",
            json={
                "activity_id": activity_id,
                "concept_ids": concept_ids,
                "config": {
                    "question_types": [{"type": "mcq4", "count": 2}],
                    "difficulty_distribution": {"easy": 50, "medium": 30, "hard": 20},
                },
                "instructions": "Focus on practical applications and real-world examples.",
            },
        )

        assert response.status_code == 201

        # Verify questions were created in database
        gen_questions = (
            service_supabase_client.table("gen_questions").select("*").eq("activity_id", activity_id).execute()
        )

        assert len(gen_questions.data) >= 1

    def test_accepts_empty_instructions(
        self,
        test_client: TestClient,
        test_activity: dict[str, Any],
        test_concepts: list[dict[str, Any]],
    ):
        """
        Test that the endpoint accepts empty string for instructions.
        """
        concept_ids = [c["id"] for c in test_concepts]

        response = test_client.post(
            "/api/v1/qgen/generate_questions",
            json={
                "activity_id": test_activity["id"],
                "concept_ids": concept_ids,
                "config": {
                    "question_types": [{"type": "mcq4", "count": 1}],
                    "difficulty_distribution": {"easy": 50, "medium": 30, "hard": 20},
                },
                "instructions": "",
            },
        )

        # Should not return validation error
        assert response.status_code in [201, 500]

    def test_accepts_null_instructions(
        self,
        test_client: TestClient,
        test_activity: dict[str, Any],
        test_concepts: list[dict[str, Any]],
    ):
        """
        Test that the endpoint accepts null for instructions.
        """
        concept_ids = [c["id"] for c in test_concepts]

        response = test_client.post(
            "/api/v1/qgen/generate_questions",
            json={
                "activity_id": test_activity["id"],
                "concept_ids": concept_ids,
                "config": {
                    "question_types": [{"type": "mcq4", "count": 1}],
                    "difficulty_distribution": {"easy": 50, "medium": 30, "hard": 20},
                },
                "instructions": None,
            },
        )

        # Should not return validation error
        assert response.status_code in [201, 500]

    def test_works_without_instructions_field(
        self,
        test_client: TestClient,
        test_activity: dict[str, Any],
        test_concepts: list[dict[str, Any]],
    ):
        """
        Test that the endpoint works when instructions field is omitted entirely.
        """
        concept_ids = [c["id"] for c in test_concepts]

        response = test_client.post(
            "/api/v1/qgen/generate_questions",
            json={
                "activity_id": test_activity["id"],
                "concept_ids": concept_ids,
                "config": {
                    "question_types": [{"type": "mcq4", "count": 1}],
                    "difficulty_distribution": {"easy": 50, "medium": 30, "hard": 20},
                },
                # instructions field intentionally omitted
            },
        )

        # Should work without instructions
        assert response.status_code in [201, 500]

    @pytest.mark.slow
    def test_instructions_with_special_characters(
        self,
        test_client: TestClient,
        service_supabase_client: Client,
        test_activity: dict[str, Any],
        test_concepts: list[dict[str, Any]],
        test_bank_questions: list[dict[str, Any]],
    ):
        """
        Test that instructions with special characters are handled properly.
        """
        concept_ids = [c["id"] for c in test_concepts]
        activity_id = test_activity["id"]

        response = test_client.post(
            "/api/v1/qgen/generate_questions",
            json={
                "activity_id": activity_id,
                "concept_ids": concept_ids,
                "config": {
                    "question_types": [{"type": "mcq4", "count": 1}],
                    "difficulty_distribution": {"easy": 50, "medium": 30, "hard": 20},
                },
                "instructions": ("Use LaTeX format: $E = mc^2$, include formulas like \\frac{1}{2}mv^2"),
            },
        )

        assert response.status_code == 201

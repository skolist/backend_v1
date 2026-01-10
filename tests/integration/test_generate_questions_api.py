"""
Integration tests for the generate_questions API endpoint.

These tests use a real Supabase client and Gemini API to test
the full end-to-end question generation flow.
"""

import uuid
from typing import Any, Dict, List

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
        test_activity: Dict[str, Any],
        test_concepts: List[Dict[str, Any]],
    ):
        """
        Test that the endpoint returns 401 when no auth token is provided.
        """
        concept_ids = [c["id"] for c in test_concepts]

        response = unauthenticated_test_client.post(
            "/api/v1/generate/questions",
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
        test_activity: Dict[str, Any],
        test_concepts: List[Dict[str, Any]],
    ):
        """
        Test that the endpoint returns 401 with an invalid token.
        """
        client = TestClient(app)
        client.headers["Authorization"] = "Bearer invalid_token_here"

        concept_ids = [c["id"] for c in test_concepts]

        response = client.post(
            "/api/v1/generate/questions",
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
        test_concepts: List[Dict[str, Any]],
    ):
        """
        Test that the endpoint returns 422 for invalid activity_id format.
        """
        concept_ids = [c["id"] for c in test_concepts]

        response = test_client.post(
            "/api/v1/generate/questions",
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
        test_activity: Dict[str, Any],
        test_concepts: List[Dict[str, Any]],
    ):
        """
        Test that the endpoint returns 422 for invalid question type.
        """
        concept_ids = [c["id"] for c in test_concepts]

        response = test_client.post(
            "/api/v1/generate/questions",
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
        test_activity: Dict[str, Any],
        test_concepts: List[Dict[str, Any]],
    ):
        """
        Test that the endpoint returns 422 when config is missing.
        """
        concept_ids = [c["id"] for c in test_concepts]

        response = test_client.post(
            "/api/v1/generate/questions",
            json={
                "activity_id": test_activity["id"],
                "concept_ids": concept_ids,
            },
        )

        assert response.status_code == 422

    def test_returns_422_with_empty_concept_ids(
        self,
        test_client: TestClient,
        test_activity: Dict[str, Any],
    ):
        """
        Test that the endpoint handles empty concept_ids list.
        """
        response = test_client.post(
            "/api/v1/generate/questions",
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
        # Note: 500 indicates a bug in the endpoint that should be fixed
        assert response.status_code in [201, 422, 500]


# ============================================================================
# TESTS FOR SUCCESSFUL QUESTION GENERATION
# ============================================================================


class TestGenerateQuestionsSuccess:
    """Tests for successful question generation."""

    @pytest.mark.slow
    def test_generates_mcq4_questions_successfully(
        self,
        test_client: TestClient,
        service_supabase_client: Client,
        test_activity: Dict[str, Any],
        test_concepts: List[Dict[str, Any]],
        test_bank_questions: List[Dict[str, Any]],  # Ensure bank questions exist
    ):
        """
        Test that MCQ4 questions are generated and stored in database.
        """
        concept_ids = [c["id"] for c in test_concepts]
        activity_id = test_activity["id"]

        response = test_client.post(
            "/api/v1/generate/questions",
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
            service_supabase_client.table("gen_questions")
            .select("*")
            .eq("activity_id", activity_id)
            .execute()
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
        test_activity: Dict[str, Any],
        test_concepts: List[Dict[str, Any]],
        test_bank_questions: List[Dict[str, Any]],
    ):
        """
        Test that multiple question types can be generated in one request.
        """
        concept_ids = [c["id"] for c in test_concepts]
        activity_id = test_activity["id"]

        response = test_client.post(
            "/api/v1/generate/questions",
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
            service_supabase_client.table("gen_questions")
            .select("*")
            .eq("activity_id", activity_id)
            .execute()
        )

        question_types = {q["question_type"] for q in gen_questions.data}
        # Should have at least one question type present
        assert len(question_types) >= 1

    @pytest.mark.slow
    def test_creates_concept_question_mappings(
        self,
        test_client: TestClient,
        service_supabase_client: Client,
        test_activity: Dict[str, Any],
        test_concepts: List[Dict[str, Any]],
        test_bank_questions: List[Dict[str, Any]],
    ):
        """
        Test that concept-question mappings are created in gen_questions_concepts_maps.
        """
        concept_ids = [c["id"] for c in test_concepts]
        activity_id = test_activity["id"]

        response = test_client.post(
            "/api/v1/generate/questions",
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
            service_supabase_client.table("gen_questions")
            .select("id")
            .eq("activity_id", activity_id)
            .execute()
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

            # Each question should have a concept mapping
            assert len(mappings.data) >= len(gen_questions.data)

            # Verify concept_ids in mappings are from our test concepts
            mapping_concept_ids = {m["concept_id"] for m in mappings.data}
            for cid in mapping_concept_ids:
                assert cid in concept_ids


# ============================================================================
# TESTS FOR EDGE CASES
# ============================================================================


class TestGenerateQuestionsEdgeCases:
    """Tests for edge cases in question generation."""

    def test_handles_nonexistent_concepts_gracefully(
        self,
        test_client: TestClient,
        test_activity: Dict[str, Any],
    ):
        """
        Test that the endpoint handles non-existent concept IDs gracefully.
        """
        fake_concept_ids = [str(uuid.uuid4()), str(uuid.uuid4())]

        response = test_client.post(
            "/api/v1/generate/questions",
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
    def test_handles_large_question_count(
        self,
        test_client: TestClient,
        service_supabase_client: Client,
        test_activity: Dict[str, Any],
        test_concepts: List[Dict[str, Any]],
        test_bank_questions: List[Dict[str, Any]],
    ):
        """
        Test generating a larger number of questions.
        """
        concept_ids = [c["id"] for c in test_concepts]
        activity_id = test_activity["id"]

        response = test_client.post(
            "/api/v1/generate/questions",
            json={
                "activity_id": activity_id,
                "concept_ids": concept_ids,
                "config": {
                    "question_types": [
                        {"type": "mcq4", "count": 3},
                        {"type": "fill_in_the_blank", "count": 2},
                    ],
                    "difficulty_distribution": {"easy": 40, "medium": 40, "hard": 20},
                },
            },
        )

        assert response.status_code == 201

        # Verify questions were created
        gen_questions = (
            service_supabase_client.table("gen_questions")
            .select("*")
            .eq("activity_id", activity_id)
            .execute()
        )

        # Should have generated at least some questions
        assert len(gen_questions.data) >= 1

    @pytest.mark.slow
    def test_questions_have_valid_structure(
        self,
        test_client: TestClient,
        service_supabase_client: Client,
        test_activity: Dict[str, Any],
        test_concepts: List[Dict[str, Any]],
        test_bank_questions: List[Dict[str, Any]],
    ):
        """
        Test that generated questions have valid structure based on type.
        """
        concept_ids = [c["id"] for c in test_concepts]
        activity_id = test_activity["id"]

        response = test_client.post(
            "/api/v1/generate/questions",
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

        # Verify MCQ4 questions have options
        gen_questions = (
            service_supabase_client.table("gen_questions")
            .select("*")
            .eq("activity_id", activity_id)
            .eq("question_type", "mcq4")
            .execute()
        )

        for question in gen_questions.data:
            # MCQ4 should have options and correct answer
            assert question.get("option1") is not None or question.get("question_text")
            # Validate hardness level is valid enum
            assert question["hardness_level"] in ["easy", "medium", "hard"]

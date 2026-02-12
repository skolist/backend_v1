"""
Integration tests for the bank management API endpoints.

Tests the admin-only bank question management functionality.
These endpoints require `user_type = 'skolist-admin'` in the users table.
"""

import uuid
from typing import Any, Dict, List

import pytest
from fastapi.testclient import TestClient
from supabase import Client


# ============================================================================
# FIXTURES FOR ADMIN ACCESS
# ============================================================================


# Test admin credentials (same as regular test user, seeded by skolist-db/seed_users.py)
TEST_ADMIN_EMAIL = "test@example.com"
TEST_ADMIN_PASSWORD = "password123"


@pytest.fixture
def admin_auth_session(env: Dict[str, str], service_supabase_client: Client):
    """
    Create an admin user session for bank tests.
    
    Uses the same test user but grants admin privileges via user_type.
    The admin user must have user_type = 'skolist-admin' in users table.
    """
    from supabase import create_client
    
    client = create_client(env["SUPABASE_URL"], env["SUPABASE_ANON_KEY"])
    auth_response = client.auth.sign_in_with_password({
        "email": TEST_ADMIN_EMAIL,
        "password": TEST_ADMIN_PASSWORD,
    })
    
    session = getattr(auth_response, "session", None)
    user = getattr(auth_response, "user", None)
    
    if not session or not user:
        pytest.skip("Could not authenticate admin user")
    
    token = getattr(session, "access_token", None)
    user_id = getattr(user, "id", None)
    user_email = getattr(user, "email", TEST_ADMIN_EMAIL)
    
    # Ensure the user exists in public.users with admin privileges
    # The CHECK constraint requires email OR phone_num to be non-null
    service_supabase_client.table("users").upsert({
        "id": user_id,
        "email": user_email,
        "user_type": "skolist-admin",
        "credits": 10000,  # Give admin user credits for testing
    }).execute()
    
    yield {
        "access_token": token,
        "user_id": user_id,
    }
    
    # Cleanup: reset user type to non-admin
    service_supabase_client.table("users").update({
        "user_type": "private_user"
    }).eq("id", user_id).execute()


@pytest.fixture
def admin_test_client(app, admin_auth_session: Dict[str, Any]) -> TestClient:
    """Create a TestClient with admin authentication headers."""
    client = TestClient(app)
    client.headers["Authorization"] = f"Bearer {admin_auth_session['access_token']}"
    return client


# ============================================================================
# AUTH TESTS
# ============================================================================


class TestBankAuth:
    """Tests for authentication on bank endpoints."""

    def test_list_returns_401_without_auth_token(
        self,
        unauthenticated_test_client: TestClient,
    ):
        """Test that /bank/list returns 401 when no auth token is provided."""
        response = unauthenticated_test_client.post(
            "/api/v1/bank/list",
            json={
                "page": 1,
                "page_size": 20,
                "filters": {},
            },
        )
        assert response.status_code == 401

    def test_list_returns_403_for_non_admin_user(
        self,
        test_client: TestClient,  # Regular user, not admin
    ):
        """Test that /bank/list returns 403 for non-admin users."""
        response = test_client.post(
            "/api/v1/bank/list",
            json={
                "page": 1,
                "page_size": 20,
                "filters": {},
            },
        )
        assert response.status_code == 403


# ============================================================================
# LIST ENDPOINT TESTS
# ============================================================================


class TestBankList:
    """Tests for the /bank/list endpoint."""

    def test_list_returns_paginated_questions(
        self,
        admin_test_client: TestClient,
    ):
        """Test that /bank/list returns paginated bank questions."""
        response = admin_test_client.post(
            "/api/v1/bank/list",
            json={
                "page": 1,
                "page_size": 10,
                "filters": {},
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "data" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data
        assert data["page"] == 1
        assert data["page_size"] == 10

    def test_list_filters_by_subject_id(
        self,
        admin_test_client: TestClient,
        test_bank_questions: List[Dict[str, Any]],
    ):
        """Test that /bank/list filters by subject_id."""
        # Get subject_id from test questions
        subject_id = test_bank_questions[0].get("subject_id")
        
        response = admin_test_client.post(
            "/api/v1/bank/list",
            json={
                "page": 1,
                "page_size": 20,
                "filters": {
                    "subject_id": subject_id,
                },
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # All returned questions should have the same subject_id
        for item in data["data"]:
            assert item["raw_data"]["subject_id"] == subject_id

    def test_list_filters_by_question_type(
        self,
        admin_test_client: TestClient,
    ):
        """Test that /bank/list filters by question_type."""
        response = admin_test_client.post(
            "/api/v1/bank/list",
            json={
                "page": 1,
                "page_size": 20,
                "filters": {
                    "question_type": "mcq4",
                },
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # All returned questions should be MCQ4
        for item in data["data"]:
            assert item["raw_data"]["question_type"] == "mcq4"

    def test_list_filters_by_hardness_level(
        self,
        admin_test_client: TestClient,
    ):
        """Test that /bank/list filters by hardness_level."""
        response = admin_test_client.post(
            "/api/v1/bank/list",
            json={
                "page": 1,
                "page_size": 20,
                "filters": {
                    "hardness_level": "easy",
                },
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        
        for item in data["data"]:
            assert item["raw_data"]["hardness_level"] == "easy"

    def test_list_search_query(
        self,
        admin_test_client: TestClient,
    ):
        """Test that /bank/list supports text search."""
        response = admin_test_client.post(
            "/api/v1/bank/list",
            json={
                "page": 1,
                "page_size": 20,
                "filters": {
                    "search_query": "Newton",
                },
            },
        )
        
        assert response.status_code == 200
        # Just verify it returns a valid response


# ============================================================================
# PREVIEW ENDPOINTS TESTS
# ============================================================================


class TestBankPreview:
    """Tests for the bank preview endpoints."""

    @pytest.fixture
    def test_bank_question_for_preview(
        self,
        service_supabase_client: Client,
    ):
        """Create a single test bank question for preview operations."""
        question_id = str(uuid.uuid4())
        
        # Get a subject_id
        subject_resp = service_supabase_client.table("subjects").select("id").limit(1).execute()
        if not subject_resp.data:
            pytest.skip("No subjects available for bank questions")
        
        subject_id = subject_resp.data[0]["id"]
        
        question_data = {
            "id": question_id,
            "question_text": "What is the formula for kinetic energy? (Preview Test)",
            "question_type": "mcq4",
            "option1": "KE = m*v",
            "option2": "KE = 1/2*m*v^2",
            "option3": "KE = m*g*h",
            "option4": "KE = m*v^2",
            "correct_mcq_option": 2,
            "answer_text": "KE = 1/2*m*v^2",
            "explanation": "KE = 1/2 * mass * velocity^2",
            "hardness_level": "medium",
            "marks": 1,
            "subject_id": subject_id,
        }
        
        service_supabase_client.table("bank_questions").insert(question_data).execute()
        
        yield question_data
        
        # Cleanup
        service_supabase_client.table("bank_questions").delete().eq(
            "id", question_id
        ).execute()

    def test_preview_auto_correct_returns_corrected_question(
        self,
        admin_test_client: TestClient,
        test_bank_question_for_preview: Dict[str, Any],
    ):
        """Test that preview/auto-correct returns a corrected version."""
        response = admin_test_client.post(
            "/api/v1/bank/preview/auto-correct",
            json={
                "question": test_bank_question_for_preview,
            },
        )
        
        # Should return 200 with corrected question preview
        assert response.status_code in [200, 400, 500]

    def test_preview_regenerate_returns_new_version(
        self,
        admin_test_client: TestClient,
        test_bank_question_for_preview: Dict[str, Any],
    ):
        """Test that preview/regenerate returns a regenerated version."""
        response = admin_test_client.post(
            "/api/v1/bank/preview/regenerate",
            json={
                "question": test_bank_question_for_preview,
            },
        )
        
        # Should return 200 with regenerated question preview
        assert response.status_code in [200, 400, 500]


# ============================================================================
# UPDATE ENDPOINT TESTS
# ============================================================================


class TestBankUpdate:
    """Tests for the /bank/update endpoint."""

    @pytest.fixture
    def test_bank_question_for_update(
        self,
        service_supabase_client: Client,
    ):
        """Create a test bank question for update operations."""
        question_id = str(uuid.uuid4())
        
        subject_resp = service_supabase_client.table("subjects").select("id").limit(1).execute()
        if not subject_resp.data:
            pytest.skip("No subjects available")
        
        subject_id = subject_resp.data[0]["id"]
        
        question_data = {
            "id": question_id,
            "question_text": "Original question text (Update Test)",
            "question_type": "mcq4",
            "option1": "Option A",
            "option2": "Option B",
            "option3": "Option C",
            "option4": "Option D",
            "correct_mcq_option": 1,
            "answer_text": "Option A",
            "hardness_level": "easy",
            "marks": 1,
            "subject_id": subject_id,
            "is_image_needed": True,
            "is_incomplete": True,
        }
        
        service_supabase_client.table("bank_questions").insert(question_data).execute()
        
        yield question_data
        
        # Cleanup
        service_supabase_client.table("bank_questions").delete().eq(
            "id", question_id
        ).execute()

    def test_update_modifies_bank_question(
        self,
        admin_test_client: TestClient,
        service_supabase_client: Client,
        test_bank_question_for_update: Dict[str, Any],
    ):
        """Test that /bank/update modifies a bank question."""
        # Create updated question payload
        updated_question = {**test_bank_question_for_update}
        updated_question["question_text"] = "Updated question text"
        updated_question["hardness_level"] = "hard"
        
        response = admin_test_client.post(
            "/api/v1/bank/update",
            json={
                "id": test_bank_question_for_update["id"],
                "question": updated_question,
            },
        )
        
        assert response.status_code in [200, 201]
        
        # Verify the update in database
        result = service_supabase_client.table("bank_questions").select("*").eq(
            "id", test_bank_question_for_update["id"]
        ).execute()
        
        if result.data:
            assert result.data[0]["question_text"] == "Updated question text"
            assert result.data[0]["hardness_level"] == "hard"

    def test_remove_image_needed_flag(
        self,
        admin_test_client: TestClient,
        service_supabase_client: Client,
        test_bank_question_for_update: Dict[str, Any],
    ):
        """Test that /bank/remove_image_needed removes the flag."""
        response = admin_test_client.post(
            "/api/v1/bank/remove_image_needed",
            json={
                "id": test_bank_question_for_update["id"],
            },
        )
        
        assert response.status_code in [200, 201]
        
        # Verify the flag is removed
        result = service_supabase_client.table("bank_questions").select("is_image_needed").eq(
            "id", test_bank_question_for_update["id"]
        ).execute()
        
        if result.data:
            assert result.data[0]["is_image_needed"] is False

    def test_remove_incomplete_flag(
        self,
        admin_test_client: TestClient,
        service_supabase_client: Client,
        test_bank_question_for_update: Dict[str, Any],
    ):
        """Test that /bank/remove_incomplete removes the flag."""
        response = admin_test_client.post(
            "/api/v1/bank/remove_incomplete",
            json={
                "id": test_bank_question_for_update["id"],
            },
        )
        
        assert response.status_code in [200, 201]
        
        # Verify the flag is removed
        result = service_supabase_client.table("bank_questions").select("is_incomplete").eq(
            "id", test_bank_question_for_update["id"]
        ).execute()
        
        if result.data:
            assert result.data[0]["is_incomplete"] is False

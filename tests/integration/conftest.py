"""
Shared fixtures for integration tests.

These fixtures provide authenticated Supabase clients, test data setup/teardown,
and FastAPI TestClient with authentication headers.
"""

import os
import uuid
from typing import Any, Dict, Generator, List

import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from supabase import Client, create_client

from app import create_app
from supabase_dir import PublicProductTypeEnumEnum


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def _get_session_access_token(auth_response) -> str | None:
    """Extract access_token from supabase-py auth response across versions."""
    session = getattr(auth_response, "session", None)
    if session is None and isinstance(auth_response, dict):
        session = auth_response.get("session")

    if session is None:
        return None

    token = getattr(session, "access_token", None)
    if token is None and isinstance(session, dict):
        token = session.get("access_token")

    return token


def _get_user_id(auth_response) -> str | None:
    """Extract user id from supabase-py auth response."""
    user = getattr(auth_response, "user", None)
    if user is None and isinstance(auth_response, dict):
        user = auth_response.get("user")

    if user is None:
        return None

    user_id = getattr(user, "id", None)
    if user_id is None and isinstance(user, dict):
        user_id = user.get("id")

    return user_id


# ============================================================================
# ENVIRONMENT FIXTURES
# ============================================================================


@pytest.fixture(scope="session")
def env() -> Dict[str, str]:
    """
    Load and validate required environment variables for integration tests.
    """
    load_dotenv()

    supabase_url = os.getenv("SUPABASE_URL")
    supabase_anon_key = os.getenv("SUPABASE_ANON_KEY")
    supabase_service_key = os.getenv("SUPABASE_SERVICE_KEY")
    test_user_email = os.getenv("TEST_USER_EMAIL")
    test_user_password = os.getenv("TEST_USER_PASSWORD")
    gemini_api_key = os.getenv("GEMINI_API_KEY")

    missing = [
        name
        for name, value in [
            ("SUPABASE_URL", supabase_url),
            ("SUPABASE_ANON_KEY", supabase_anon_key),
            ("SUPABASE_SERVICE_KEY", supabase_service_key),
            ("TEST_USER_EMAIL", test_user_email),
            ("TEST_USER_PASSWORD", test_user_password),
            ("GEMINI_API_KEY", gemini_api_key),
        ]
        if not value
    ]
    if missing:
        pytest.skip(
            "Missing env vars for integration tests: " + ", ".join(missing)
        )

    return {
        "SUPABASE_URL": supabase_url,
        "SUPABASE_ANON_KEY": supabase_anon_key,
        "SUPABASE_SERVICE_KEY": supabase_service_key,
        "TEST_USER_EMAIL": test_user_email,
        "TEST_USER_PASSWORD": test_user_password,
        "GEMINI_API_KEY": gemini_api_key,
    }


# ============================================================================
# SUPABASE CLIENT FIXTURES
# ============================================================================


@pytest.fixture(scope="session")
def service_supabase_client(env: Dict[str, str]) -> Client:
    """
    Create a Supabase client with service role key.
    Used for test data setup/teardown operations.
    """
    return create_client(env["SUPABASE_URL"], env["SUPABASE_SERVICE_KEY"])


@pytest.fixture(scope="session")
def auth_session(env: Dict[str, str]) -> Dict[str, Any]:
    """
    Authenticate as test user and return session info.
    """
    client = create_client(env["SUPABASE_URL"], env["SUPABASE_ANON_KEY"])
    auth_response = client.auth.sign_in_with_password(
        {
            "email": env["TEST_USER_EMAIL"],
            "password": env["TEST_USER_PASSWORD"],
        }
    )

    token = _get_session_access_token(auth_response)
    user_id = _get_user_id(auth_response)

    if not token:
        pytest.fail("Failed to get access token from Supabase sign-in")

    if not user_id:
        pytest.fail("Failed to get user ID from Supabase sign-in")

    return {
        "access_token": token,
        "user_id": user_id,
    }


# ============================================================================
# FASTAPI TEST CLIENT FIXTURES
# ============================================================================


@pytest.fixture(scope="session")
def app():
    """
    Create the FastAPI application instance.
    """
    return create_app()


@pytest.fixture(scope="session")
def test_client(app, auth_session: Dict[str, Any]) -> TestClient:
    """
    Create a TestClient with authentication headers.
    """
    client = TestClient(app)
    # Set default headers for all requests
    client.headers["Authorization"] = f"Bearer {auth_session['access_token']}"
    return client


@pytest.fixture
def unauthenticated_test_client(app) -> TestClient:
    """
    Create a TestClient without authentication headers.
    """
    return TestClient(app)


# ============================================================================
# TEST DATA FIXTURES
# ============================================================================


@pytest.fixture(scope="module")
def test_topic_id(service_supabase_client: Client) -> Generator[str, None, None]:
    """
    Get or create a test topic for concept creation.
    We need a valid topic_id since concepts require it.
    """
    # First, try to get an existing topic
    response = service_supabase_client.table("topics").select("id").limit(1).execute()

    if response.data and len(response.data) > 0:
        yield response.data[0]["id"]
    else:
        # If no topics exist, we need to create the hierarchy:
        # board -> school_class -> subject -> chapter -> topic

        # Check for existing board
        board_resp = (
            service_supabase_client.table("boards").select("id").limit(1).execute()
        )
        if board_resp.data:
            board_id = board_resp.data[0]["id"]
        else:
            board_id = str(uuid.uuid4())
            service_supabase_client.table("boards").insert(
                {"id": board_id, "name": "Test Board"}
            ).execute()

        # Check for existing school_class
        class_resp = (
            service_supabase_client.table("school_classes")
            .select("id")
            .limit(1)
            .execute()
        )
        if class_resp.data:
            class_id = class_resp.data[0]["id"]
        else:
            class_id = str(uuid.uuid4())
            service_supabase_client.table("school_classes").insert(
                {
                    "id": class_id,
                    "name": "Test Class",
                    "board_id": board_id,
                    "position": 1,
                }
            ).execute()

        # Check for existing subject
        subject_resp = (
            service_supabase_client.table("subjects").select("id").limit(1).execute()
        )
        if subject_resp.data:
            subject_id = subject_resp.data[0]["id"]
        else:
            subject_id = str(uuid.uuid4())
            service_supabase_client.table("subjects").insert(
                {"id": subject_id, "name": "Test Subject", "school_class_id": class_id}
            ).execute()

        # Check for existing chapter
        chapter_resp = (
            service_supabase_client.table("chapters").select("id").limit(1).execute()
        )
        if chapter_resp.data:
            chapter_id = chapter_resp.data[0]["id"]
        else:
            chapter_id = str(uuid.uuid4())
            service_supabase_client.table("chapters").insert(
                {"id": chapter_id, "name": "Test Chapter", "subject_id": subject_id}
            ).execute()

        # Create topic
        topic_id = str(uuid.uuid4())
        service_supabase_client.table("topics").insert(
            {
                "id": topic_id,
                "name": "Test Topic",
                "chapter_id": chapter_id,
                "position": 1,
            }
        ).execute()

        yield topic_id

        # Cleanup: We won't delete the hierarchy to avoid breaking other tests


@pytest.fixture
def test_concepts(
    service_supabase_client: Client,
    test_topic_id: str,
) -> Generator[List[Dict[str, Any]], None, None]:
    """
    Create test concepts in Supabase and clean up after test.
    """
    concept_ids = [str(uuid.uuid4()), str(uuid.uuid4())]

    concepts_data = [
        {
            "id": concept_ids[0],
            "name": "Newton's Laws of Motion",
            "description": "The three fundamental laws describing the relationship between forces and motion.",
            "topic_id": test_topic_id,
            "page_number": 1,
        },
        {
            "id": concept_ids[1],
            "name": "Kinetic Energy",
            "description": "Energy possessed by an object due to its motion. Formula: KE = 1/2 * m * v^2.",
            "topic_id": test_topic_id,
            "page_number": 2,
        },
    ]

    # Insert concepts
    response = service_supabase_client.table("concepts").insert(concepts_data).execute()

    yield response.data

    # Cleanup: Delete test concepts
    service_supabase_client.table("concepts").delete().in_(
        "id", concept_ids
    ).execute()


@pytest.fixture
def test_activity(
    service_supabase_client: Client,
    auth_session: Dict[str, Any],
) -> Generator[Dict[str, Any], None, None]:
    """
    Create a test activity in Supabase and clean up after test.
    """
    activity_id = str(uuid.uuid4())
    user_id = auth_session["user_id"]

    activity_data = {
        "id": activity_id,
        "name": "Test Activity for Question Generation",
        "product_type": PublicProductTypeEnumEnum.QGEN.value,
        "user_id": user_id,
    }

    # Insert activity
    response = (
        service_supabase_client.table("activities").insert(activity_data).execute()
    )

    yield response.data[0]

    # Cleanup: First delete related data, then delete activity
    # Delete gen_questions_concepts_maps entries
    gen_questions = (
        service_supabase_client.table("gen_questions")
        .select("id")
        .eq("activity_id", activity_id)
        .execute()
    )

    if gen_questions.data:
        question_ids = [q["id"] for q in gen_questions.data]
        service_supabase_client.table("gen_questions_concepts_maps").delete().in_(
            "gen_question_id", question_ids
        ).execute()

        # Delete gen_questions
        service_supabase_client.table("gen_questions").delete().eq(
            "activity_id", activity_id
        ).execute()

    # Delete the activity
    service_supabase_client.table("activities").delete().eq(
        "id", activity_id
    ).execute()


@pytest.fixture
def test_bank_questions(
    service_supabase_client: Client,
    test_concepts: List[Dict[str, Any]],
) -> Generator[List[Dict[str, Any]], None, None]:
    """
    Create test bank questions (historical questions) for the concepts.
    These are used as reference data for question generation.
    """
    # Get a subject_id for the bank questions
    subject_resp = (
        service_supabase_client.table("subjects").select("id").limit(1).execute()
    )

    if not subject_resp.data:
        pytest.skip("No subjects available for bank questions")

    subject_id = subject_resp.data[0]["id"]

    question_ids = [str(uuid.uuid4()), str(uuid.uuid4())]
    concept_ids = [c["id"] for c in test_concepts]

    bank_questions_data = [
        {
            "id": question_ids[0],
            "question_text": "What is Newton's First Law of Motion?",
            "question_type": "mcq4",
            "option1": "Law of Inertia",
            "option2": "Law of Acceleration",
            "option3": "Law of Action-Reaction",
            "option4": "Law of Gravity",
            "correct_mcq_option": 1,
            "answer_text": "Law of Inertia",
            "explanation": "Newton's First Law states that an object at rest stays at rest.",
            "hardness_level": "easy",
            "marks": 1,
            "subject_id": subject_id,
        },
        {
            "id": question_ids[1],
            "question_text": "Calculate the kinetic energy of a 2kg object moving at 3 m/s.",
            "question_type": "short_answer",
            "answer_text": "KE = 1/2 * 2 * 3^2 = 9 Joules",
            "explanation": "Using the formula KE = 1/2 * m * v^2",
            "hardness_level": "medium",
            "marks": 2,
            "subject_id": subject_id,
        },
    ]

    # Insert bank questions
    response = (
        service_supabase_client.table("bank_questions")
        .insert(bank_questions_data)
        .execute()
    )

    # Create mappings between bank questions and concepts
    mappings_data = [
        {
            "id": str(uuid.uuid4()),
            "bank_question_id": question_ids[0],
            "concept_id": concept_ids[0],
        },
        {
            "id": str(uuid.uuid4()),
            "bank_question_id": question_ids[1],
            "concept_id": concept_ids[1],
        },
    ]

    service_supabase_client.table("bank_questions_concepts_maps").insert(
        mappings_data
    ).execute()

    yield response.data

    # Cleanup: Delete mappings first, then questions
    service_supabase_client.table("bank_questions_concepts_maps").delete().in_(
        "bank_question_id", question_ids
    ).execute()

    service_supabase_client.table("bank_questions").delete().in_(
        "id", question_ids
    ).execute()

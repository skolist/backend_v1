"""
Test integration of Supabase authentication with FastAPI endpoint.
"""

import os

import pytest

from dotenv import load_dotenv
from fastapi.testclient import TestClient
from supabase import create_client

from app import create_app


# Hardcoded test credentials - must match skolist-db/seed_users.py
TEST_USER_EMAIL = "test@example.com"
TEST_USER_PASSWORD = "password123"


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


@pytest.fixture(scope="session")
def env() -> dict:
    """
    Function to load required environment variables for Supabase auth tests.
    Uses hardcoded test credentials that match skolist-db/seed_users.py.
    """
    load_dotenv()

    supabase_url = os.getenv("SUPABASE_URL")
    supabase_anon_key = os.getenv("SUPABASE_ANON_KEY")

    missing = [
        name
        for name, value in [
            ("SUPABASE_URL", supabase_url),
            ("SUPABASE_ANON_KEY", supabase_anon_key),
        ]
        if not value
    ]
    if missing:
        pytest.skip("Missing env vars for Supabase sign-in: " + ", ".join(missing))

    # API-side verification uses SUPABASE_SERVICE_KEY via config/settings.py.
    if not os.getenv("SUPABASE_SERVICE_KEY"):
        pytest.skip("Missing SUPABASE_SERVICE_KEY for API verification")

    return {
        "SUPABASE_URL": supabase_url,
        "SUPABASE_ANON_KEY": supabase_anon_key,
        "TEST_USER_EMAIL": TEST_USER_EMAIL,
        "TEST_USER_PASSWORD": TEST_USER_PASSWORD,
    }


@pytest.fixture()
def client() -> TestClient:
    """
    Fixture to create a TestClient for the FastAPI app tests.
    """
    app = create_app()
    return TestClient(app)


def test_hello_without_token_is_401(client: TestClient) -> None:
    """
    Test accessing the /api/v1/hello endpoint without a token returns 401.
    """
    resp = client.get("/api/v1/hello")
    assert resp.status_code == 401


def test_hello_with_supabase_jwt_is_200(client: TestClient, env: dict) -> None:
    """
    Test accessing the /api/v1/hello endpoint with a valid Supabase JWT returns 200.
    """
    supabase = create_client(env["SUPABASE_URL"], env["SUPABASE_ANON_KEY"])
    auth_resp = supabase.auth.sign_in_with_password(
        {
            "email": env["TEST_USER_EMAIL"],
            "password": env["TEST_USER_PASSWORD"],
        }
    )

    token = _get_session_access_token(auth_resp)
    assert token, "No access_token returned from Supabase sign-in"

    resp = client.get("/api/v1/hello", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200

    payload = resp.json()
    assert payload.get("authenticated") is True
    assert payload.get("message") == "hello"

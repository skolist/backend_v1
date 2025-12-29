import os

import pytest

from dotenv import load_dotenv
from fastapi.testclient import TestClient
from supabase import create_client

from app import create_app


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
    load_dotenv()

    supabase_url = os.getenv("SUPABASE_URL")
    supabase_anon_key = os.getenv("SUPABASE_ANON_KEY")
    test_user_email = os.getenv("TEST_USER_EMAIL")
    test_user_password = os.getenv("TEST_USER_PASSWORD")

    missing = [
        name
        for name, value in [
            ("SUPABASE_URL", supabase_url),
            ("SUPABASE_ANON_KEY", supabase_anon_key),
            ("TEST_USER_EMAIL", test_user_email),
            ("TEST_USER_PASSWORD", test_user_password),
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
        "TEST_USER_EMAIL": test_user_email,
        "TEST_USER_PASSWORD": test_user_password,
    }


@pytest.fixture()
def client() -> TestClient:
    app = create_app()
    return TestClient(app)


def test_hello_without_token_is_401(client: TestClient) -> None:
    resp = client.get("/api/v1/hello")
    assert resp.status_code == 401


def test_hello_with_supabase_jwt_is_200(client: TestClient, env: dict) -> None:
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

import os
import unittest

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


class TestSupabaseAuthHello(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        load_dotenv()

        cls.supabase_url = os.getenv("SUPABASE_URL")
        cls.supabase_anon_key = os.getenv("SUPABASE_ANON_KEY")
        cls.test_user_email = os.getenv("TEST_USER_EMAIL")
        cls.test_user_password = os.getenv("TEST_USER_PASSWORD")

        missing = [
            name
            for name, value in [
                ("SUPABASE_URL", cls.supabase_url),
                ("SUPABASE_ANON_KEY", cls.supabase_anon_key),
                ("TEST_USER_EMAIL", cls.test_user_email),
                ("TEST_USER_PASSWORD", cls.test_user_password),
            ]
            if not value
        ]

        if missing:
            raise unittest.SkipTest(
                "Missing env vars for Supabase sign-in: " + ", ".join(missing)
            )

        # App-level auth verification uses SUPABASE_SERVICE_KEY via config/settings.py.
        if not os.getenv("SUPABASE_SERVICE_KEY"):
            raise unittest.SkipTest("Missing SUPABASE_SERVICE_KEY for API verification")

        cls.app = create_app()
        cls.client = TestClient(cls.app)

    def test_hello_without_token_is_401(self) -> None:
        resp = self.client.get("/api/v1/hello")
        self.assertEqual(resp.status_code, 401)

    def test_hello_with_supabase_jwt_is_200(self) -> None:
        supabase = create_client(self.supabase_url, self.supabase_anon_key)
        auth_resp = supabase.auth.sign_in_with_password(
            {
                "email": self.test_user_email,
                "password": self.test_user_password,
            }
        )

        token = _get_session_access_token(auth_resp)
        self.assertTrue(token, "No access_token returned from Supabase sign-in")

        resp = self.client.get(
            "/api/v1/hello", headers={"Authorization": f"Bearer {token}"}
        )
        self.assertEqual(resp.status_code, 200)

        payload = resp.json()
        self.assertTrue(payload.get("authenticated"))
        self.assertEqual(payload.get("message"), "hello")


if __name__ == "__main__":
    unittest.main()

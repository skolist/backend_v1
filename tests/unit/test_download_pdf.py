from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from api.v1.auth import get_supabase_client, require_supabase_user
from app import create_app

# Mock data
MOCK_DRAFT = {"id": "test-draft", "paper_title": "Test Paper", "institute_name": "Test Inst"}
MOCK_SECTIONS = [{"id": "sec-1", "section_name": "Section 1", "position_in_draft": 1}]
MOCK_QUESTIONS = [
    {
        "id": "q-1",
        "qgen_draft_section_id": "sec-1",
        "question_text": "Q1",
        "marks": 5,
        "is_in_draft": True,
    }
]
MOCK_INSTRUCTIONS = []
MOCK_IMAGES = []


class MockSupabaseClient:
    def __init__(self):
        self.table_name = None

    def table(self, name):
        self.table_name = name
        return self

    def select(self, *args, **kwargs):
        return self

    def eq(self, *args, **kwargs):
        return self

    def in_(self, *args, **kwargs):
        return self

    def order(self, *args, **kwargs):
        return self

    def execute(self):
        mock_res = MagicMock()
        if self.table_name == "qgen_drafts":
            mock_res.data = [MOCK_DRAFT]
        elif self.table_name == "qgen_draft_sections":
            mock_res.data = MOCK_SECTIONS
        elif self.table_name == "gen_questions":
            mock_res.data = MOCK_QUESTIONS
        elif self.table_name == "qgen_draft_instructions_drafts_maps":
            mock_res.data = MOCK_INSTRUCTIONS
        elif self.table_name == "gen_images":
            mock_res.data = MOCK_IMAGES
        else:
            mock_res.data = []
        return mock_res


@pytest.fixture
def test_app():
    """
    Creates the app and triggers the lifespan (startup/shutdown)
    while mocking BrowserService to avoid launching a real browser.
    """
    with patch("services.browser_service.async_playwright") as mock_ap_service:
        # Mock the playwright instance returned by .start()
        mock_p_instance = AsyncMock()
        mock_ap_service.return_value.start = AsyncMock(return_value=mock_p_instance)

        # Mock the browser returned by .chromium.launch()
        mock_browser = AsyncMock()
        mock_p_instance.chromium.launch = AsyncMock(return_value=mock_browser)

        # Setup the mock browser to return mock contexts/pages
        mock_context = AsyncMock()
        mock_page = AsyncMock()
        mock_browser.new_context.return_value = mock_context
        mock_context.new_page.return_value = mock_page
        mock_page.pdf.return_value = b"%PDF-service-content"
        # Also mock screenshot for completeness if needed
        mock_page.query_selector.return_value.screenshot.return_value = b"%PNG-content"

        app = create_app()
        # Using context manager triggers the lifespan
        with TestClient(app) as client:
            # Inject dependency overrides
            app.dependency_overrides[get_supabase_client] = lambda: MockSupabaseClient()
            app.dependency_overrides[require_supabase_user] = lambda: {"id": "test-user"}
            yield client, app, mock_browser


def test_download_pdf_working(test_app):
    """
    Test 1: Verify the endpoint works and returns a PDF using the browser service.
    """
    client, app, mock_browser = test_app

    response = client.post("/api/v1/qgen/download_pdf", json={"draft_id": "test-draft", "mode": "paper"})

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content == b"%PDF-service-content"

    # Verify the browser initialized by the service was used
    mock_browser.new_context.assert_called()


def test_browser_instance_efficiency(test_app):
    """
    Test 2: Verify multiple API hits reuse the service/browser.
    """
    client, app, mock_browser = test_app

    # Hit the endpoint 3 times
    for _ in range(3):
        response = client.post("/api/v1/qgen/download_pdf", json={"draft_id": "test-draft", "mode": "paper"})
        assert response.status_code == 200

    # Ensure context creation happened 3 times
    assert mock_browser.new_context.call_count >= 3

    # Verify we aren't creating new BrowserService instances (implied by lifespan fixture)


def test_error_if_service_missing_in_app_state(test_app):
    """
    Test 3: Verify it returns 503 if app.state.browser_service is missing.
    """
    client, app, _ = test_app

    # Intentionally break the state
    app.state.browser_service = None

    response = client.post("/api/v1/qgen/download_pdf", json={"draft_id": "test-draft", "mode": "paper"})

    assert response.status_code == 503
    assert "unavailable" in response.json()["detail"].lower()

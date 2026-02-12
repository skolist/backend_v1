from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from api.v1.auth import get_supabase_client, require_supabase_user
from app import create_app

# Basic Mock data
MOCK_DRAFT = {"id": "test-draft", "paper_title": "Test Paper", "institute_name": "Test Inst"}
MOCK_SECTIONS = [{"id": "sec-1", "section_name": "Section 1", "position_in_draft": 1}]
MOCK_QUESTIONS = [
    {
        "id": "q-1",
        "qgen_draft_section_id": "sec-1",
        "question_text": "Q1 $x^2$",
        "marks": 5,
        "is_in_draft": True,
    }
]


# Helper to mock fetch_paper_data return value
def mock_paper_data(questions=None):
    return {
        "draft": MOCK_DRAFT,
        "sections": MOCK_SECTIONS,
        "questions": questions if questions else MOCK_QUESTIONS,
        "instructions": [],
        "logo_url": None,
        "images_map": {},
    }


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
        mock_res.data = []
        # Minimal implementation for the dependency override,
        # though we primarily patch fetch_paper_data in specific tests
        return mock_res

    def storage(self):
        return MagicMock()


@pytest.fixture
def test_app():
    # Only patch app start, not concerned with PDF browser here since we are testing DOCX
    # But we must mock browser_service.async_playwright to prevent real launch
    with patch("services.browser_service.async_playwright") as mock_ap_service:
        mock_p_instance = AsyncMock()
        mock_ap_service.return_value.start = AsyncMock(return_value=mock_p_instance)
        mock_p_instance.chromium.launch = AsyncMock(return_value=AsyncMock())

        app = create_app()
        with TestClient(app) as client:
            app.dependency_overrides[get_supabase_client] = lambda: MockSupabaseClient()
            app.dependency_overrides[require_supabase_user] = lambda: {"id": "test-user"}
            yield client


def test_download_docx_working(test_app):
    """
    Test: Verify the DOCX endpoint works and renders math via math2docx.
    """
    client = test_app

    with patch("api.v1.qgen.download_docx.fetch_paper_data", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = mock_paper_data()

        with patch("api.v1.qgen.download_docx.math2docx.add_math") as mock_add_math:
            response = client.post(
                "/api/v1/qgen/download_docx", json={"draft_id": "test-draft", "mode": "paper"}
            )

            assert response.status_code == 200
            assert (
                response.headers["content-type"]
                == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )

            # Verify math2docx was called for the latex content "x^2"
            mock_add_math.assert_called()
            calls = [c[0][1] for c in mock_add_math.call_args_list]
            assert "x^2" in calls


def test_download_docx_page_break(test_app):
    """
    Test: Verify doc.add_page_break() is called when question has is_page_break_below=True.
    """
    client = test_app

    qs = [
        {
            "id": "q-1",
            "qgen_draft_section_id": "sec-1",
            "question_text": "Q1",
            "marks": 5,
            "is_page_break_below": True,
        },
        {"id": "q-2", "qgen_draft_section_id": "sec-1", "question_text": "Q2", "marks": 5},
    ]

    with patch("api.v1.qgen.download_docx.fetch_paper_data", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = mock_paper_data(questions=qs)

        # Patch Document to inspect add_page_break invocations
        with patch("api.v1.qgen.download_docx.Document") as mock_doc_cls:
            mock_doc = MagicMock()
            mock_doc_cls.return_value = mock_doc
            # Mock style access to avoid errors
            mock_doc.styles.__getitem__.return_value.font.name = "Test"

            response = client.post(
                "/api/v1/qgen/download_docx", json={"draft_id": "test-draft", "mode": "paper"}
            )

            assert response.status_code == 200
            # Should be called exactly once because only one question has the flag
            assert mock_doc.add_page_break.call_count == 1


def test_download_docx_rollback_on_math_failure(test_app):
    """
    Test: Verify that if math2docx fails, the rollback logic removes corrupted elements
    and falls back to inserting the original text using add_run.
    """
    client = test_app

    latex_text = r"$\cos\theta$"
    qs = [
        {
            "id": "q-1",
            "qgen_draft_section_id": "sec-1",
            "question_text": f"Math: {latex_text}",
            "marks": 5,
        }
    ]

    with patch("api.v1.qgen.download_docx.fetch_paper_data", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = mock_paper_data(questions=qs)

        # Patch Document to control paragraph behavior
        with patch("api.v1.qgen.download_docx.Document") as mock_doc_cls:
            mock_doc = MagicMock()
            mock_doc_cls.return_value = mock_doc
            mock_doc.styles.__getitem__.return_value.font.name = "Test"

            # Create a mock paragraph
            mock_paragraph = MagicMock()
            mock_doc.add_paragraph.return_value = mock_paragraph

            # Mock the internal list _p (lxml element list)
            # We need it to be a real list so we can test append/remove logic if we want,
            # but for this test, we primarily want to see if the fallback 'add_run' is called.
            # The rollback logic accesses len(paragraph._p).
            mock_paragraph._p = MagicMock()
            mock_paragraph._p.__len__.return_value = 0  # Simulate empty initially

            # We need to simulate math2docx failing
            with patch("api.v1.qgen.download_docx.math2docx.add_math") as mock_add_math:
                mock_add_math.side_effect = Exception("Simulated Math Failure")

                response = client.post(
                    "/api/v1/qgen/download_docx", json={"draft_id": "test-draft", "mode": "paper"}
                )

                assert response.status_code == 200

                # Check that add_math was attempted
                mock_add_math.assert_called()

                # Check that simple text fallback occurred
                # The fallback would call paragraph.add_run(part) where part is the latex string
                # Note: add_text_with_math will split "Math: $\cos\theta$" into ["Math: ", "$\cos\theta$", ""]
                # So we expect add_run to be called with the latex part.

                # Filter calls to find the one with our latex
                run_calls = [
                    args[0][0] for args in mock_paragraph.add_run.call_args_list if args[0]
                ]
                # The latex part includes the delimiters in the fallback logic: "$\cos\theta$"
                assert latex_text in run_calls

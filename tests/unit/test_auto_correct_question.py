"""
Unit tests for auto-correct service logic.

These tests validate the new refactored architecture in `api.v1.qgen.auto_correct.service`:
    1. process_question() - Single Gemini call via AutoCorrectService
    2. process_and_validate() - Calls process_question + validates response
    3. correct_question() - Integration flow (mocked)
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from api.v1.qgen.auto_correct.service import (
    AutoCorrectService,
    generate_screenshot,
)
from api.v1.qgen.models import MCQ4

# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def mock_mcq4_question() -> dict:
    return {
        "id": "550e8400-e29b-41d4-a716-446655440001",
        "question_text": "What is the formula for kinetc energy? (note the misspelling)",
        "question_type": "mcq4",
        "option1": "KE = m*v^2",
        "option2": "KE = 1/2*m*v",
        "option3": "KE = 1/2*m*v^2",
        "option4": "KE = m*g*h",
        "correct_mcq_option": 3,
        "explanation": "The kinetic energy formula is KE = half of mass times velocity squared",
        "hardness_level": "medium",
        "marks": 2,
        "activity_id": "660e8400-e29b-41d4-a716-446655440001",
    }


@pytest.fixture
def mock_browser_service():
    service = AsyncMock()
    service.take_screenshot = AsyncMock(return_value=b"fake_png_bytes")
    # If using generate_pdf too
    service.generate_pdf = AsyncMock(return_value=b"fake_pdf_bytes")
    return service

    # ... (omitted MockSupabaseClient / same as before) ...

    # ...

    @pytest.mark.asyncio
    async def test_correct_question_flow(
        self, mock_mcq4_question: dict, mock_browser_service, mock_supabase
    ):
        # Mock generic Gemini client for this specific test to avoid real calls
        mock_gemini = MagicMock()
        mock_gemini.aio.models.generate_content = AsyncMock()

        # Mock successful response
        mock_response = MagicMock()
        # Mock the parsed response structure: response.parsed.question -> MCQ4 object
        mock_mcq = MCQ4(**mock_mcq4_question)
        mock_mcq.question_text = "Corrected Text"  # Change something to verify

        mock_response.parsed.question = mock_mcq
        mock_gemini.aio.models.generate_content.return_value = mock_response

        with patch("api.v1.qgen.auto_correct.service.genai.Client", return_value=mock_gemini):
            success = await AutoCorrectService.correct_question(
                gen_question_data=mock_mcq4_question,
                gen_question_id=mock_mcq4_question["id"],
                supabase_client=mock_supabase,
                browser_service=mock_browser_service,
            )

            assert success is True

            # Verify browser usage
            mock_browser_service.take_screenshot.assert_called_once()

            # Verify DB update
            mock_supabase.table.assert_called_with("gen_questions")
            mock_supabase.table().update.assert_called()


class TestGenerateScreenshot:
    @pytest.mark.asyncio
    async def test_generate_screenshot_calls_service(
        self, mock_mcq4_question: dict, mock_browser_service
    ):
        """
        Test that generate_screenshot calls browser_service.take_screenshot.
        """
        screenshot = await generate_screenshot(mock_mcq4_question, mock_browser_service)

        # Verify result
        assert screenshot == b"fake_png_bytes"

        # Verify interactions
        mock_browser_service.take_screenshot.assert_called_once()

        call_args = mock_browser_service.take_screenshot.call_args
        kwargs = call_args.kwargs
        html_content = kwargs.get("html_content")

        # Basic HTML validation
        assert "<!DOCTYPE html>" in html_content
        assert mock_mcq4_question["question_text"] in html_content
        assert "katex.min.css" in html_content

        # Verify options
        assert kwargs.get("selector") == "body"
        assert kwargs.get("screenshot_options") == {"type": "png"}
        assert kwargs.get("context_options") == {"device_scale_factor": 2}

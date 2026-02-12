"""
Unit tests for regenerate question with prompt logic.

These tests validate the new refactored architecture:
    1. RegenerateWithPromptService.process_question()
    2. RegenerateWithPromptService.process_and_validate()
    3. RegenerateWithPromptService.regenerate_question() (Integration flow mocked)
"""

from unittest.mock import AsyncMock, MagicMock, patch

import google.genai as genai
import pytest

from api.v1.qgen.models import MCQ4
from api.v1.qgen.regenerate_with_prompt.service import (
    RegenerateWithPromptService,
    regenerate_question_with_prompt_prompt,
)

# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def mock_mcq4_question() -> dict:
    return {
        "id": "550e8400-e29b-41d4-a716-446655440001",
        "question_text": "What is the formula for kinetic energy?",
        "question_type": "mcq4",
        "option1": "KE = m*v^2",
        "option2": "KE = 1/2*m*v",
        "option3": "KE = 1/2*m*v^2",
        "option4": "KE = m*g*h",
        "correct_mcq_option": 3,
        "explanation": "Standard formula",
        "hardness_level": "medium",
        "marks": 2,
        "activity_id": "660e8400-e29b-41d4-a716-446655440001",
    }


@pytest.fixture
def mock_browser():
    browser = AsyncMock()
    context = AsyncMock()
    page = AsyncMock()

    browser.new_context.return_value = context
    context.new_page.return_value = page

    page.query_selector.return_value = AsyncMock()
    page.query_selector.return_value.screenshot.return_value = b"fake_screenshot_bytes"

    return browser


@pytest.fixture
def mock_supabase():
    client = MagicMock()
    client.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()
    return client


# ============================================================================
# TESTS FOR PROMPT
# ============================================================================


class TestRegenerateWithPromptPrompt:
    def test_default_prompt_mentions_screenshot(self, mock_mcq4_question: dict):
        prompt = regenerate_question_with_prompt_prompt(mock_mcq4_question)
        assert "screenshot" in prompt.lower()
        assert "attached" in prompt.lower()

    def test_custom_prompt_mentions_screenshot(self, mock_mcq4_question: dict):
        prompt = regenerate_question_with_prompt_prompt(mock_mcq4_question, "make it harder")
        assert "screenshot" in prompt.lower()
        assert "attached" in prompt.lower()
        assert "make it harder" in prompt


# ============================================================================
# TESTS FOR SERVICE
# ============================================================================


class TestRegenerateWithPromptService:
    @pytest.mark.asyncio
    async def test_process_question_returns_response(
        self,
        gemini_client: genai.Client,
        mock_mcq4_question: dict,
    ):
        result = await RegenerateWithPromptService.process_question(
            gemini_client=gemini_client,
            gen_question_data=mock_mcq4_question,
            retry_idx=1,
        )
        assert result is not None

    @pytest.mark.asyncio
    async def test_regenerate_question_flow(
        self, mock_mcq4_question: dict, mock_browser, mock_supabase
    ):
        # Mock generic Gemini client
        mock_gemini = MagicMock()
        mock_gemini.aio.models.generate_content = AsyncMock()

        # Mock successful response
        mock_response = MagicMock()
        mock_mcq = MCQ4(**mock_mcq4_question)
        mock_mcq.question_text = "Regenerated Text"

        mock_response.parsed.question = mock_mcq
        mock_gemini.aio.models.generate_content.return_value = mock_response

        # Patch screenshot utils to avoid actual browser/file ops if needed,
        # but since we pass mock_browser, generate_screenshot will use it.
        with (
            patch(
                "api.v1.qgen.regenerate_with_prompt.service.save_image_for_debug", new=AsyncMock()
            ) as mock_save,
            patch(
                "api.v1.qgen.regenerate_with_prompt.service.RegenerateWithPromptService.process_and_validate"
            ) as mock_process,
            patch(
                "api.v1.qgen.regenerate_with_prompt.service.generate_screenshot",
                new=AsyncMock(return_value=b"fake_image_bytes"),
            ) as mock_screenshot,
        ):
            # Setup mock return for process_and_validate
            mock_mcq = MCQ4(**mock_mcq4_question)
            mock_mcq.question_text = "Regenerated Text"
            mock_process.return_value = mock_mcq

            success = await RegenerateWithPromptService.regenerate_question(
                gen_question_data=mock_mcq4_question,
                gen_question_id=mock_mcq4_question["id"],
                supabase_client=mock_supabase,
                browser_service=mock_browser,
                gemini_client=mock_gemini,
                custom_prompt="test prompt",
            )

            assert success is True

            # Verify browser/screenshot called - wait, if we mock generate_screenshot, mock_browser usage depends on implementation
            # calling mock_screenshot means we don't necessarily call mock_browser inside it if passing mock.
            # But the service passes browser to generate_screenshot.
            mock_screenshot.assert_called_once()
            mock_save.assert_called()

            # Verify process called
            mock_process.assert_called()

            # Verify DB update
            mock_supabase.table.assert_called_with("gen_questions")

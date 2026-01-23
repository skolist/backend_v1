"""
Unit tests for auto-correct service logic.

These tests validate the new refactored architecture in `api.v1.qgen.auto_correct.service`:
    1. process_question() - Single Gemini call via AutoCorrectService
    2. process_and_validate() - Calls process_question + validates response
    3. correct_question() - Integration flow (mocked)
"""

import pytest
import google.genai as genai
from unittest.mock import AsyncMock, MagicMock, patch

from api.v1.qgen.auto_correct.service import (
    AutoCorrectService,
    QuestionProcessingError,
    QuestionValidationError,
    auto_correct_questions_prompt,
    generate_screenshot
)
from api.v1.qgen.models import MCQ4, ShortAnswer, AutoCorrectedQuestion

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
def mock_browser():
    browser = AsyncMock()
    context = AsyncMock()
    page = AsyncMock()
    
    browser.new_context.return_value = context
    context.new_page.return_value = page
    # Mock return context manager behavior
    # (browser.new_context is an async context manager in Playwright but in our code we await it directly?
    # Wait, in the code: context = await browser.new_context() -> returns context object.
    # But context itself is closed with await context.close(). 
    # Let's verify usage in service.py:
    # context = await browser.new_context(...)
    # page = await context.new_page()
    # ...
    # await page.close()
    # await context.close()
    
    page.query_selector.return_value = AsyncMock()
    page.query_selector.return_value.screenshot.return_value = b"fake_png_bytes"
    
    return browser

@pytest.fixture
def mock_supabase():
    client = MagicMock()
    client.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()
    return client

# ============================================================================
# TESTS FOR AutoCorrectService
# ============================================================================

class TestAutoCorrectService:

    @pytest.mark.asyncio
    async def test_process_question_returns_response(
        self,
        gemini_client: genai.Client,
        mock_mcq4_question: dict,
    ):
        result = await AutoCorrectService.process_question(
            gemini_client=gemini_client,
            gen_question_data=mock_mcq4_question,
            retry_idx=1,
        )
        assert result is not None
        # In mock client, result might be MagicMock, but it should simulate response structure
        # if using the conftest.py gemini_client fixture which returns a real-ish structure or mock.
        # Assuming gemini_client return value has .parsed if configured so.

    @pytest.mark.asyncio
    async def test_process_and_validate_returns_validated_question(
        self,
        gemini_client: genai.Client,
        mock_mcq4_question: dict,
    ):
        # We need to ensure the gemini_client fixture behaves as expected for the new schema
        # If it uses real Gemini, it's fine. If it uses Mock, we need to ensure structure matches.
        
        # Assuming integration/live or sophisticated mock in conftest.
        # For unit test with mock, we might need to patch generation if conftest doesn't cover this schema
        
        result = await AutoCorrectService.process_and_validate(
            gemini_client=gemini_client,
            gen_question_data=mock_mcq4_question,
            retry_idx=1,
        )

        assert result is not None
        assert isinstance(result, (MCQ4, ShortAnswer)) # or matches one of AllQuestions types
        assert result.question_text is not None


    @pytest.mark.asyncio
    async def test_correct_question_flow(
        self,
        mock_mcq4_question: dict,
        mock_browser,
        mock_supabase
    ):
        # Mock generic Gemini client for this specific test to avoid real calls
        mock_gemini = MagicMock()
        mock_gemini.aio.models.generate_content = AsyncMock()
        
        # Mock successful response
        mock_response = MagicMock()
        # Mock the parsed response structure: response.parsed.question -> MCQ4 object
        mock_mcq = MCQ4(**mock_mcq4_question)
        mock_mcq.question_text = "Corrected Text" # Change something to verify
        
        mock_response.parsed.question = mock_mcq
        mock_gemini.aio.models.generate_content.return_value = mock_response
        
        with patch("api.v1.qgen.auto_correct.service.genai.Client", return_value=mock_gemini):
            success = await AutoCorrectService.correct_question(
                gen_question_data=mock_mcq4_question,
                gen_question_id=mock_mcq4_question["id"],
                supabase_client=mock_supabase,
                browser=mock_browser
            )
            
            assert success is True
            
            # Verify browser usage
            mock_browser.new_context.assert_called_once()
            
            # Verify DB update
            mock_supabase.table.assert_called_with("gen_questions")
            mock_supabase.table().update.assert_called()


class TestAutoCorrectQuestionsPrompt:
    def test_returns_string(self, mock_mcq4_question: dict):
        prompt = auto_correct_questions_prompt(mock_mcq4_question)
        assert isinstance(prompt, str)
        assert len(prompt) > 0

    def test_includes_question_data(self, mock_mcq4_question: dict):
        prompt = auto_correct_questions_prompt(mock_mcq4_question)
        assert "kinetc" in prompt
        assert "mcq4" in prompt or "question_type" in prompt


class TestGenerateScreenshot:
    
    @pytest.mark.asyncio
    async def test_generate_screenshot_calls_playwright(
        self,
        mock_mcq4_question: dict,
        mock_browser
    ):
        """
        Test that generate_screenshot creates a page, sets content, and takes a screenshot.
        """
        screenshot = await generate_screenshot(mock_mcq4_question, mock_browser)
        
        # Verify result
        assert screenshot == b"fake_png_bytes"
        
        # Verify interactions
        mock_browser.new_context.assert_called_once()
        context = mock_browser.new_context.return_value
        context.new_page.assert_called_once()
        page = context.new_page.return_value
        
        # Verify content setting
        page.set_content.assert_called_once()
        call_args = page.set_content.call_args
        html_content = call_args[0][0]
        
        # Basic HTML validation
        assert "<!DOCTYPE html>" in html_content
        assert mock_mcq4_question["question_text"] in html_content
        assert "katex.min.css" in html_content
        
        # Verify screenshot capture
        page.query_selector.assert_called_with("body")
        element = page.query_selector.return_value
        element.screenshot.assert_called_once_with(type="png")
        
        # Verify cleanup
        page.close.assert_called_once()
        context.close.assert_called_once()

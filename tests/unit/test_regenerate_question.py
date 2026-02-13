"""
Unit tests for regenerate question logic.

These tests use a Gemini client (mock by default, real with --gemini-live)
to validate the new refactored architecture:
    1. process_question() - Single Gemini call (no retries)
    2. process_question_and_validate() - Calls process_question + validates response
"""

import google.genai as genai
import pytest

from api.v1.qgen.models import MCQ4, ShortAnswer
from api.v1.qgen.regenerate_question import (
    QuestionProcessingError,
    QuestionValidationError,
    process_question,
    process_question_and_validate,
    regenerate_question_prompt,
)

# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def mock_mcq4_question() -> dict:
    """
    Mock an MCQ4 question data for regeneration testing.
    """
    return {
        "id": "550e8400-e29b-41d4-a716-446655440001",
        "question_text": "What is the formula for kinetic energy?",
        "question_type": "mcq4",
        "option1": "KE = m*v^2",
        "option2": "KE = 1/2*m*v",
        "option3": "KE = 1/2*m*v^2",
        "option4": "KE = m*g*h",
        "correct_mcq_option": 3,
        "explanation": "The kinetic energy formula is KE = 1/2 * m * v^2",
        "hardness_level": "medium",
        "marks": 2,
        "activity_id": "660e8400-e29b-41d4-a716-446655440001",
    }


@pytest.fixture
def mock_short_answer_question() -> dict:
    """
    Mock a short answer question data for regeneration testing.
    """
    return {
        "id": "550e8400-e29b-41d4-a716-446655440002",
        "question_text": ("What is Newton's first law of motion? Explain in simple terms."),
        "question_type": "short_answer",
        "answer_text": ("An object in motion will stay in motion unless acted upon by an external force."),
        "explanation": (
            "This is the law of inertia. The state of motion of an object changes only when a force is applied."
        ),
        "hardness_level": "easy",
        "marks": 3,
        "activity_id": "660e8400-e29b-41d4-a716-446655440001",
    }


@pytest.fixture
def mock_latex_question() -> dict:
    """
    Mock a question with LaTeX that contains curly braces (potential format issue).
    """
    return {
        "id": "550e8400-e29b-41d4-a716-446655440003",
        "question_text": r"If $\sin^2\theta = \frac{1}{3}$, what is the value of $\cos^2\theta$?",
        "question_type": "short_answer",
        "answer_text": r"$\cos^2\theta = \frac{2}{3}$",
        "explanation": "Using the identity sin²θ + cos²θ = 1",
        "hardness_level": "medium",
        "marks": 2,
        "activity_id": "660e8400-e29b-41d4-a716-446655440001",
    }


# ============================================================================
# TESTS FOR regenerate_question_prompt
# ============================================================================


class TestRegenerateQuestionPrompt:
    """Tests for the regenerate_question_prompt function."""

    def test_returns_string(self, mock_mcq4_question: dict):
        """
        Test that regenerate_question_prompt returns a string.
        """
        prompt = regenerate_question_prompt(mock_mcq4_question)
        assert isinstance(prompt, str)
        assert len(prompt) > 0

    def test_includes_question_data(self, mock_mcq4_question: dict):
        """
        Test that prompt includes the question data.
        """
        prompt = regenerate_question_prompt(mock_mcq4_question)
        assert "kinetic" in prompt.lower()
        assert "mcq4" in prompt or "question_type" in prompt

    def test_prompt_instructs_to_regenerate(self, mock_short_answer_question: dict):
        """
        Test that prompt contains regeneration instructions.
        """
        prompt = regenerate_question_prompt(mock_short_answer_question)
        assert "same concepts" in prompt.lower() or "new question" in prompt.lower()

    def test_handles_latex_with_curly_braces(self, mock_latex_question: dict):
        """
        Test that prompt handles LaTeX with curly braces (no format error).

        This tests the fix for: "Replacement index 1 out of range for positional args tuple"
        """
        # This should NOT raise an error
        prompt = regenerate_question_prompt(mock_latex_question)
        assert isinstance(prompt, str)
        # The LaTeX should be included in the prompt
        assert "frac" in prompt or "sin" in prompt

    def test_includes_latex_error_instructions(self, mock_mcq4_question: dict):
        """
        Test that prompt includes LaTeX error instructions.
        """
        prompt = regenerate_question_prompt(mock_mcq4_question)
        assert "Common Latex Errors" in prompt
        assert "$" in prompt  # Should mention $$ symbols


# ============================================================================
# TESTS FOR process_question
# ============================================================================


class TestProcessQuestion:
    """Tests for the process_question function."""

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_returns_response(
        self,
        gemini_client: genai.Client,
        mock_mcq4_question: dict,
    ):
        """
        Test that process_question returns a Gemini response.
        """
        result = await process_question(
            gemini_client=gemini_client,
            gen_question_data=mock_mcq4_question,
            retry_idx=1,
        )

        # Should return a response object
        assert result is not None
        assert hasattr(result, "parsed")

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_works_with_short_answer(
        self,
        gemini_client: genai.Client,
        mock_short_answer_question: dict,
    ):
        """
        Test that process_question works with short answer questions.
        """
        result = await process_question(
            gemini_client=gemini_client,
            gen_question_data=mock_short_answer_question,
            retry_idx=1,
        )

        assert result is not None
        assert hasattr(result, "parsed")

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_works_with_latex_question(
        self,
        gemini_client: genai.Client,
        mock_latex_question: dict,
    ):
        """
        Test that process_question handles LaTeX questions correctly.
        """
        result = await process_question(
            gemini_client=gemini_client,
            gen_question_data=mock_latex_question,
            retry_idx=1,
        )

        assert result is not None
        assert hasattr(result, "parsed")


# ============================================================================
# TESTS FOR process_question_and_validate
# ============================================================================


class TestProcessQuestionAndValidate:
    """Tests for the process_question_and_validate function."""

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_returns_regenerated_question(
        self,
        gemini_client: genai.Client,
        mock_mcq4_question: dict,
    ):
        """
        Test that process_question_and_validate returns a regenerated question.
        """
        result = await process_question_and_validate(
            gemini_client=gemini_client,
            gen_question_data=mock_mcq4_question,
            retry_idx=1,
        )

        # Should return a question object (one of the AllQuestions union types)
        assert result is not None
        assert hasattr(result, "question_text")
        assert isinstance(result.question_text, str)

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_regenerates_mcq4_question_with_options(
        self,
        gemini_client: genai.Client,
        mock_mcq4_question: dict,
    ):
        """
        Test that regenerated MCQ4 questions have valid options.
        """
        result = await process_question_and_validate(
            gemini_client=gemini_client,
            gen_question_data=mock_mcq4_question,
            retry_idx=1,
        )

        # For MCQ4, should have options if it's an MCQ4 type
        if isinstance(result, MCQ4):
            # Options should exist and be non-empty
            assert result.option1 is not None
            assert result.option2 is not None
            assert result.option3 is not None
            assert result.option4 is not None

            # Correct option should be set
            assert result.correct_mcq_option is not None
            assert 1 <= result.correct_mcq_option <= 4

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_regenerates_short_answer_question(
        self,
        gemini_client: genai.Client,
        mock_short_answer_question: dict,
    ):
        """
        Test that short answer questions are regenerated properly.
        """
        result = await process_question_and_validate(
            gemini_client=gemini_client,
            gen_question_data=mock_short_answer_question,
            retry_idx=1,
        )

        # For short answer, should have regenerated answer_text
        if isinstance(result, ShortAnswer):
            assert result.answer_text is not None
            assert len(result.answer_text) > 0

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_preserves_same_concept(
        self,
        gemini_client: genai.Client,
        mock_mcq4_question: dict,
    ):
        """
        Test that the regenerated question is about the same concept.
        """
        result = await process_question_and_validate(
            gemini_client=gemini_client,
            gen_question_data=mock_mcq4_question,
            retry_idx=1,
        )

        # The regenerated question should still be about kinetic energy
        question_text = result.question_text.lower()
        # At least one of these concepts should be present
        assert any(concept in question_text for concept in ["kinetic", "energy", "velocity", "motion", "mass"])

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_returns_valid_pydantic_model(
        self,
        gemini_client: genai.Client,
        mock_mcq4_question: dict,
    ):
        """
        Test that the result is a valid Pydantic model.
        """
        result = await process_question_and_validate(
            gemini_client=gemini_client,
            gen_question_data=mock_mcq4_question,
            retry_idx=1,
        )

        # Should have model_dump method (Pydantic v2)
        assert hasattr(result, "model_dump")
        dumped = result.model_dump()
        assert isinstance(dumped, dict)

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_regenerated_question_has_explanation(
        self,
        gemini_client: genai.Client,
        mock_mcq4_question: dict,
    ):
        """
        Test that the regenerated question includes an explanation.
        """
        result = await process_question_and_validate(
            gemini_client=gemini_client,
            gen_question_data=mock_mcq4_question,
            retry_idx=1,
        )

        # Should have explanation
        if hasattr(result, "explanation"):
            assert result.explanation is not None
            assert len(result.explanation) > 0


# ============================================================================
# TESTS FOR CUSTOM EXCEPTIONS
# ============================================================================


class TestCustomExceptions:
    """Tests for custom exception classes."""

    def test_question_processing_error_is_exception(self):
        """Test that QuestionProcessingError is an Exception."""
        error = QuestionProcessingError("Test error message")
        assert isinstance(error, Exception)
        assert str(error) == "Test error message"

    def test_question_validation_error_is_exception(self):
        """Test that QuestionValidationError is an Exception."""
        error = QuestionValidationError("Validation failed")
        assert isinstance(error, Exception)
        assert str(error) == "Validation failed"

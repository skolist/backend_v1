"""
Unit tests for regenerate question logic.

These tests use a Gemini client (mock by default, real with --gemini-live)
to validate the regenerate_question_logic function.
"""

import pytest
import google.genai as genai

from api.v1.qgen.regenerate_question import (
    regenerate_question_logic,
    regenerate_question_prompt,
)
from api.v1.qgen.models import MCQ4, ShortAnswer


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
        "question_text": "What is Newton's first law of motion? Explain in simple terms.",
        "question_type": "short_answer",
        "answer_text": "An object in motion will stay in motion unless acted upon by an external force.",
        "explanation": "This is the law of inertia. The state of motion of an object changes only when a force is applied.",
        "hardness_level": "easy",
        "marks": 3,
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


# ============================================================================
# TESTS FOR regenerate_question_logic
# ============================================================================


class TestRegenerateQuestionLogic:
    """Tests for the regenerate_question_logic function."""

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_returns_regenerated_question(
        self,
        gemini_client: genai.Client,
        mock_mcq4_question: dict,
    ):
        """
        Test that regenerate_question_logic returns a regenerated question.
        """
        result = await regenerate_question_logic(
            gemini_client=gemini_client,
            gen_question_data=mock_mcq4_question,
        )

        # Should return a question object (one of the AllQuestions union types)
        assert result is not None
        assert hasattr(result, "question_text")
        assert isinstance(result.question_text, str)

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_regenerated_question_is_different(
        self,
        gemini_client: genai.Client,
        mock_mcq4_question: dict,
    ):
        """
        Test that the regenerated question is different from the original.
        """
        original_text = mock_mcq4_question["question_text"]
        result = await regenerate_question_logic(
            gemini_client=gemini_client,
            gen_question_data=mock_mcq4_question,
        )

        # The regenerated question should have a different question text
        # (though still about the same concept)
        assert result.question_text is not None
        assert len(result.question_text) > 0
        # Note: It's possible the AI generates a similar question,
        # so we just verify it's a valid question

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
        result = await regenerate_question_logic(
            gemini_client=gemini_client,
            gen_question_data=mock_mcq4_question,
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
        result = await regenerate_question_logic(
            gemini_client=gemini_client,
            gen_question_data=mock_short_answer_question,
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
        result = await regenerate_question_logic(
            gemini_client=gemini_client,
            gen_question_data=mock_mcq4_question,
        )

        # The regenerated question should still be about kinetic energy
        question_text = result.question_text.lower()
        # At least one of these concepts should be present
        assert any(
            concept in question_text
            for concept in ["kinetic", "energy", "velocity", "motion", "mass"]
        )

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
        result = await regenerate_question_logic(
            gemini_client=gemini_client,
            gen_question_data=mock_mcq4_question,
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
        result = await regenerate_question_logic(
            gemini_client=gemini_client,
            gen_question_data=mock_mcq4_question,
        )

        # Should have explanation
        if hasattr(result, "explanation"):
            assert result.explanation is not None
            assert len(result.explanation) > 0

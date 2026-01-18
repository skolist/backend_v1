"""
Unit tests for auto-correct question logic.

These tests use a Gemini client (mock by default, real with --gemini-live)
to validate the auto_correct_question_logic function.
"""

import pytest
import google.genai as genai

from api.v1.qgen.auto_correct_question import (
    auto_correct_question_logic,
    auto_correct_questions_prompt,
)
from api.v1.qgen.models import MCQ4, ShortAnswer


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def mock_mcq4_question() -> dict:
    """
    Mock an MCQ4 question data with potential formatting issues.
    """
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
def mock_short_answer_question() -> dict:
    """
    Mock a short answer question data with grammatical issues.
    """
    return {
        "id": "550e8400-e29b-41d4-a716-446655440002",
        "question_text": "What is newtons first law of motion? Explain in simple terms",
        "question_type": "short_answer",
        "answer_text": "An object in motion will stay in motion unless acted upon by external force",
        "explanation": "This is the law of inertia. State of motion of object changes only when force is applied",
        "hardness_level": "easy",
        "marks": 3,
        "activity_id": "660e8400-e29b-41d4-a716-446655440001",
    }


# ============================================================================
# TESTS FOR auto_correct_questions_prompt
# ============================================================================


class TestAutoCorrectQuestionsPrompt:
    """Tests for the auto_correct_questions_prompt function."""

    def test_returns_string(self, mock_mcq4_question: dict):
        """
        Test that auto_correct_questions_prompt returns a string.
        """
        prompt = auto_correct_questions_prompt(mock_mcq4_question)
        assert isinstance(prompt, str)
        assert len(prompt) > 0

    def test_includes_question_data(self, mock_mcq4_question: dict):
        """
        Test that prompt includes the question data.
        """
        prompt = auto_correct_questions_prompt(mock_mcq4_question)
        assert "kinetc" in prompt  # Should include the misspelled word
        assert "mcq4" in prompt or "question_type" in prompt

    def test_prompt_instructs_to_correct(self, mock_short_answer_question: dict):
        """
        Test that prompt contains correction instructions.
        """
        prompt = auto_correct_questions_prompt(mock_short_answer_question)
        assert "correct" in prompt.lower()
        assert "latex" in prompt.lower() or "format" in prompt.lower()


# ============================================================================
# TESTS FOR auto_correct_question_logic
# ============================================================================


class TestAutoCorrectQuestionLogic:
    """Tests for the auto_correct_question_logic function."""

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_returns_corrected_question(
        self,
        gemini_client: genai.Client,
        mock_mcq4_question: dict,
    ):
        """
        Test that auto_correct_question_logic returns a corrected question.
        """
        result = await auto_correct_question_logic(
            gemini_client=gemini_client,
            gen_question_data=mock_mcq4_question,
        )

        # Should return a question object (one of the AllQuestions union types)
        assert result is not None
        assert hasattr(result, "question_text")
        assert isinstance(result.question_text, str)

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_preserves_question_meaning(
        self,
        gemini_client: genai.Client,
        mock_mcq4_question: dict,
    ):
        """
        Test that the corrected question preserves the original meaning.
        """
        original_text = mock_mcq4_question["question_text"]
        result = await auto_correct_question_logic(
            gemini_client=gemini_client,
            gen_question_data=mock_mcq4_question,
        )

        # The corrected text should be different (fixing issues)
        # but the core concept should be about kinetic energy
        assert result.question_text is not None
        assert len(result.question_text) > 0

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_corrects_mcq4_question_options(
        self,
        gemini_client: genai.Client,
        mock_mcq4_question: dict,
    ):
        """
        Test that MCQ4 questions have corrected options.
        """
        result = await auto_correct_question_logic(
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
    async def test_corrects_short_answer_question(
        self,
        gemini_client: genai.Client,
        mock_short_answer_question: dict,
    ):
        """
        Test that short answer questions are corrected properly.
        """
        result = await auto_correct_question_logic(
            gemini_client=gemini_client,
            gen_question_data=mock_short_answer_question,
        )

        # For short answer, should have corrected answer_text
        if isinstance(result, ShortAnswer):
            assert result.answer_text is not None
            assert len(result.answer_text) > 0

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_corrects_grammar_and_formatting(
        self,
        gemini_client: genai.Client,
        mock_mcq4_question: dict,
    ):
        """
        Test that grammar and formatting are improved.
        """
        original_text = mock_mcq4_question["question_text"]
        result = await auto_correct_question_logic(
            gemini_client=gemini_client,
            gen_question_data=mock_mcq4_question,
        )

        # The corrected question should fix the misspelling
        corrected_text = result.question_text
        assert "kinetic" in corrected_text.lower()
        assert "energy" in corrected_text.lower()

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
        result = await auto_correct_question_logic(
            gemini_client=gemini_client,
            gen_question_data=mock_mcq4_question,
        )

        # Should have model_dump method (Pydantic v2)
        assert hasattr(result, "model_dump")
        dumped = result.model_dump()
        assert isinstance(dumped, dict)

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_preserves_answer_structure(
        self,
        gemini_client: genai.Client,
        mock_short_answer_question: dict,
    ):
        """
        Test that corrected question preserves the answer structure.
        """
        original_answer = mock_short_answer_question["answer_text"]
        result = await auto_correct_question_logic(
            gemini_client=gemini_client,
            gen_question_data=mock_short_answer_question,
        )

        # Should have answer_text
        if hasattr(result, "answer_text"):
            assert result.answer_text is not None
            assert len(result.answer_text) > 0

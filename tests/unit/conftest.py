"""
Shared fixtures for unit tests.

Provides a mock/live Gemini client based on --gemini-live flag.
The --gemini-live option is defined in tests/conftest.py.
"""

import os
from typing import Any
from unittest.mock import MagicMock

import google.genai as genai
import pytest
from dotenv import load_dotenv

from api.v1.qgen.models import MCQ4, FillInTheBlank, ShortAnswer, TrueFalse

# ============================================================================
# MOCK RESPONSE FACTORIES
# ============================================================================


def create_mock_mcq4(question_text: str | None = None) -> MCQ4:
    """Create a mock MCQ4 question."""
    return MCQ4(
        question_text=question_text or "What is the formula for kinetic energy?",
        option1="KE = m*v^2",
        option2="KE = 1/2*m*v",
        option3="KE = 1/2*m*v^2",
        option4="KE = m*g*h",
        correct_mcq_option=3,
        explanation="The kinetic energy formula is KE = 1/2 * m * v^2",
    )


def create_mock_short_answer(question_text: str | None = None) -> ShortAnswer:
    """Create a mock ShortAnswer question."""
    return ShortAnswer(
        question_text=question_text or "Explain Newton's first law of motion.",
        answer_text="An object in motion stays in motion unless acted upon by an external force.",
        explanation="This is the law of inertia.",
    )


def create_mock_true_false(question_text: str | None = None) -> TrueFalse:
    """Create a mock TrueFalse question."""
    return TrueFalse(
        question_text=question_text or "Kinetic energy depends on velocity squared.",
        correct_answer=True,
        explanation="KE = 1/2 * m * v^2, so it depends on v squared.",
    )


def create_mock_fill_in_blank(question_text: str | None = None) -> FillInTheBlank:
    """Create a mock FillInTheBlank question."""
    return FillInTheBlank(
        question_text=question_text or "The formula for kinetic energy is KE = 1/2 * m * ___",
        answer_text="v^2",
        explanation="Velocity squared completes the kinetic energy formula.",
    )


# ============================================================================
# MOCK GEMINI CLIENT
# ============================================================================


class MockParsedResponse:
    """Mock for response.parsed and response.text attributes."""

    def __init__(self, parsed_obj: Any, text: str = ""):
        self._parsed = parsed_obj
        self._text = text

    @property
    def parsed(self):
        return self._parsed

    @property
    def text(self):
        return self._text


class MockQuestionsResponse:
    """Mock for questions response with .questions attribute."""

    def __init__(self, questions: list):
        self.questions = questions


class MockGeminiModels:
    """Mock for gemini_client.aio.models."""

    def __init__(self):
        self._call_count = 0

    async def generate_content(
        self,
        model: str,
        contents: Any,
        config: dict,
    ) -> MockParsedResponse:
        """Mock generate_content that returns appropriate responses based on schema."""
        schema = config.get("response_schema")
        schema_name = getattr(schema, "__name__", str(schema))
        contents_str = str(contents).lower()

        # Handle auto-correct endpoint (returns wrapper with .question)
        if "AutoCorrected" in schema_name:
            # Check if it's a short answer based on input
            if "short_answer" in contents_str:

                class QuestionWrapper:
                    question = create_mock_short_answer("What is Newton's first law of motion?")

                return MockParsedResponse(QuestionWrapper())
            else:

                class QuestionWrapper:
                    question = create_mock_mcq4("What is the formula for kinetic energy?")

                return MockParsedResponse(QuestionWrapper())

        # Handle regenerate endpoints (returns wrapper with .question)
        if "Regenerated" in schema_name:
            # Check if it's a short answer based on input
            if "short_answer" in contents_str:

                class QuestionWrapper:
                    question = create_mock_short_answer(
                        "Describe the principle of conservation of momentum."
                    )

                return MockParsedResponse(QuestionWrapper())
            else:

                class QuestionWrapper:
                    question = create_mock_mcq4(
                        "Calculate the kinetic energy of a 5kg object moving at 10 m/s."
                    )

                return MockParsedResponse(QuestionWrapper())

        # Handle feedback endpoint (returns FeedbackList with .feedbacks list)
        if "FeedbackList" in schema_name or "feedback" in contents_str:
            from api.v1.qgen.models import FeedbackItem, FeedbackList

            feedback_list = FeedbackList(
                feedbacks=[
                    FeedbackItem(
                        message="Consider adding more variety in question difficulty levels.",
                        priority=7,
                    ),
                    FeedbackItem(
                        message="Some questions could benefit from clearer wording.", priority=5
                    ),
                ]
            )
            return MockParsedResponse(feedback_list)

        # Handle question generation schemas (returns wrapper with .questions list)
        if "mcq4" in contents_str:
            questions = MockQuestionsResponse([create_mock_mcq4()])
            return MockParsedResponse(questions)

        if "true_false" in contents_str:
            questions = MockQuestionsResponse([create_mock_true_false()])
            return MockParsedResponse(questions)

        if "fill_in_the_blank" in contents_str:
            questions = MockQuestionsResponse([create_mock_fill_in_blank()])
            return MockParsedResponse(questions)

        if "short_answer" in contents_str:
            questions = MockQuestionsResponse([create_mock_short_answer()])
            return MockParsedResponse(questions)

        # Default: return MCQ4 questions list
        questions = MockQuestionsResponse([create_mock_mcq4()])
        return MockParsedResponse(questions)


class MockAioNamespace:
    """Mock for gemini_client.aio namespace."""

    def __init__(self):
        self.models = MockGeminiModels()


class MockGeminiClient:
    """Mock Gemini client that mimics real client interface."""

    def __init__(self):
        self.aio = MockAioNamespace()
        # Also provide sync interface for compatibility
        self.models = MagicMock()


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture(scope="session")
def gemini_client(use_live_gemini) -> genai.Client:
    """
    Provide Gemini client - mock by default, real with --gemini-live flag.

    Usage:
        pytest tests/unit/                    # Uses mock client
        pytest tests/unit/ --gemini-live      # Uses real API
    """
    if use_live_gemini:
        load_dotenv()
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            pytest.skip("GEMINI_API_KEY not set in environment")
        return genai.Client(api_key=api_key)
    else:
        return MockGeminiClient()

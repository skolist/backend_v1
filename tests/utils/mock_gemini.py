"""
Shared Gemini mock implementation for unit and integration tests.

This module provides a MockGeminiClient that mimics the real google.genai.Client
interface, returning realistic question structures based on the request context.

Usage:
    from tests.utils.mock_gemini import MockGeminiClient

    # Patch in conftest.py:
    with patch("api.v1.qgen.module.genai.Client", MockGeminiClient):
        ...
"""

from typing import Any
from unittest.mock import MagicMock

from api.v1.qgen.models import MCQ4, FillInTheBlank, ShortAnswer, TrueFalse

# ============================================================================
# MOCK RESPONSE FACTORIES
# ============================================================================


def create_mock_mcq4(question_text: str | None = None) -> MCQ4:
    """Create a mock MCQ4 question with realistic content."""
    return MCQ4(
        question_text=question_text or "What is the formula for kinetic energy?",
        option1="KE = m*v^2",
        option2="KE = 1/2*m*v",
        option3="KE = 1/2*m*v^2",
        option4="KE = m*g*h",
        correct_mcq_option=3,
        explanation="The kinetic energy formula is KE = 1/2 * m * v^2",
        answer_text="KE = 1/2*m*v^2",
        hardness_level="medium",
        marks=1,
    )


def create_mock_short_answer(question_text: str | None = None) -> ShortAnswer:
    """Create a mock ShortAnswer question with realistic content."""
    return ShortAnswer(
        question_text=question_text or "Explain Newton's first law of motion.",
        answer_text="An object in motion stays in motion unless acted upon by an external force.",
        explanation="This is the law of inertia.",
        hardness_level="medium",
        marks=2,
    )


def create_mock_true_false(question_text: str | None = None) -> TrueFalse:
    """Create a mock TrueFalse question with realistic content."""
    return TrueFalse(
        question_text=question_text or "Kinetic energy depends on velocity squared.",
        correct_answer=True,
        explanation="KE = 1/2 * m * v^2, so it depends on v squared.",
        answer_text="True",
        hardness_level="easy",
        marks=1,
    )


def create_mock_fill_in_blank(question_text: str | None = None) -> FillInTheBlank:
    """Create a mock FillInTheBlank question with realistic content."""
    return FillInTheBlank(
        question_text=question_text or "The formula for kinetic energy is KE = 1/2 * m * ___",
        answer_text="v^2",
        explanation="Velocity squared completes the kinetic energy formula.",
        hardness_level="medium",
        marks=1,
    )


# ============================================================================
# MOCK RESPONSE WRAPPERS
# ============================================================================


class MockParsedResponse:
    """Mock for Gemini API response with both .parsed and .text attributes."""

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


# ============================================================================
# MOCK GEMINI CLIENT
# ============================================================================


class MockGeminiModels:
    """Mock for gemini_client.aio.models that handles generate_content calls."""

    def __init__(self):
        self._call_count = 0

    async def generate_content(
        self,
        model: str,
        contents: Any,
        config: dict,
    ) -> MockParsedResponse:
        """
        Mock generate_content that returns appropriate responses based on schema.

        Analyzes the schema name and content to determine what type of question
        to return, mimicking real Gemini API behavior.
        """
        self._call_count += 1
        schema = config.get("response_schema")
        schema_name = getattr(schema, "__name__", str(schema)) if schema else ""
        contents_str = str(contents).lower()

        # Handle edit_svg endpoint (unstructured response - uses .text, no schema)
        if (not schema or schema is None) and ("svg" in contents_str or "edit" in contents_str):
            mock_svg = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200">
    <circle cx="100" cy="100" r="75" fill="blue"/>
    <text x="100" y="100" text-anchor="middle">r = 75</text>
</svg>"""
            return MockParsedResponse(None, text=mock_svg)

        # Handle auto-correct endpoint (returns wrapper with .question)
        if "AutoCorrected" in schema_name:
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
            if "short_answer" in contents_str:

                class QuestionWrapper:
                    question = create_mock_short_answer("Describe the principle of conservation of momentum.")

                return MockParsedResponse(QuestionWrapper())
            else:

                class QuestionWrapper:
                    question = create_mock_mcq4("Calculate the kinetic energy of a 5kg object moving at 10 m/s.")

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
                    FeedbackItem(message="Some questions could benefit from clearer wording.", priority=5),
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
    """
    Mock Gemini client that mimics real google.genai.Client interface.

    Provides both sync and async interfaces for compatibility with
    different parts of the codebase.

    Usage:
        # In tests
        with patch("module.genai.Client", MockGeminiClient):
            result = await some_function_that_uses_gemini()
    """

    def __init__(self, *args, **kwargs):
        # Accept any arguments (like api_key) but ignore them
        self.aio = MockAioNamespace()
        # Also provide sync interface for compatibility
        self.models = MagicMock()


# ============================================================================
# MOCK BROWSER SERVICE
# ============================================================================


class MockBrowserService:
    """
    Mock BrowserService for tests to avoid real Playwright startup.

    Used for PDF generation and screenshot operations.
    """

    def __init__(self):
        self.browser = "mock_browser_instance"

    async def start(self):
        """Mock start - does nothing."""
        pass

    async def stop(self):
        """Mock stop - does nothing."""
        pass

    async def take_screenshot(self, *args, **kwargs):
        """Return fake screenshot bytes."""
        return b"fake_screenshot_bytes"

    async def generate_pdf(self, *args, **kwargs):
        """Return fake PDF bytes."""
        return b"%PDF-1.4 fake pdf content"


# ============================================================================
# GEMINI PATCH TARGETS
# ============================================================================

# All modules where genai.Client is instantiated and needs patching
GEMINI_PATCH_TARGETS = [
    "api.v1.qgen.generate_questions.routes.genai.Client",
    "api.v1.qgen.auto_correct.service.genai.Client",
    "api.v1.qgen.regenerate_question.genai.Client",
    "api.v1.qgen.regenerate_with_prompt.routes.genai.Client",
    "api.v1.qgen.get_feedback.genai.Client",
    "api.v1.qgen.edit_svg.service.genai.Client",
    "api.v1.bank.router.genai.Client",
]

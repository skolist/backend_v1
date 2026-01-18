"""
Shared fixtures for integration tests.

These fixtures provide authenticated Supabase clients, test data setup/teardown,
and FastAPI TestClient with authentication headers.

By default, tests use a mock Gemini client. Use --gemini-live to test with real API.
The --gemini-live option is defined in tests/conftest.py.
"""

import os
import uuid
from typing import Any, Dict, Generator, List
from unittest.mock import patch

import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from supabase import Client, create_client

from app import create_app
from supabase_dir import PublicProductTypeEnumEnum
from api.v1.qgen.models import MCQ4, ShortAnswer, TrueFalse, FillInTheBlank
from api.v1.qgen.question_generator import (
    ConceptQuestionTypeDistribution,
    ConceptDistributionItem,
    QuestionTypeDistribution,
)


# ============================================================================
# MOCK RESPONSE FACTORIES (for integration tests)
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
        answer_text="KE = 1/2*m*v^2",
        hardness_level="medium",
        marks=1,
    )


def create_mock_short_answer(question_text: str | None = None) -> ShortAnswer:
    """Create a mock ShortAnswer question."""
    return ShortAnswer(
        question_text=question_text or "Explain Newton's first law of motion.",
        answer_text="An object in motion stays in motion unless acted upon by an external force.",
        explanation="This is the law of inertia.",
        hardness_level="medium",
        marks=2,
    )


def create_mock_true_false(question_text: str | None = None) -> TrueFalse:
    """Create a mock TrueFalse question."""
    return TrueFalse(
        question_text=question_text or "Kinetic energy depends on velocity squared.",
        correct_answer=True,
        explanation="KE = 1/2 * m * v^2, so it depends on v squared.",
        answer_text="True",
        hardness_level="easy",
        marks=1,
    )


def create_mock_fill_in_blank(question_text: str | None = None) -> FillInTheBlank:
    """Create a mock FillInTheBlank question."""
    return FillInTheBlank(
        question_text=question_text or "The formula for kinetic energy is KE = 1/2 * m * ___",
        answer_text="v^2",
        explanation="Velocity squared completes the kinetic energy formula.",
        hardness_level="medium",
        marks=1,
    )


def create_mock_distribution(
    concept_names: list[str],
    requested_types: dict[str, int] | None = None,
) -> ConceptQuestionTypeDistribution:
    """
    Create a mock distribution for the given concepts.
    
    Args:
        concept_names: List of concept names
        requested_types: Dict mapping question type to requested count.
                        If None, defaults to mcq4 only.
    """
    if requested_types is None:
        # Default to just mcq4
        requested_types = {"mcq4": 2}
    
    distribution = []
    total_concepts = len(concept_names)
    
    for i, name in enumerate(concept_names):
        # Distribute questions across concepts
        counts = QuestionTypeDistribution(
            mcq4=0,
            msq4=0,
            fill_in_the_blank=0,
            true_false=0,
            short_answer=0,
            long_answer=0,
        )
        
        # Distribute each requested type evenly across concepts
        for qtype, total_count in requested_types.items():
            if total_count > 0:
                # Give first concept the majority
                if i == 0:
                    count_for_concept = (total_count + total_concepts - 1) // total_concepts
                else:
                    count_for_concept = total_count // total_concepts
                
                if hasattr(counts, qtype):
                    setattr(counts, qtype, count_for_concept)
        
        distribution.append(
            ConceptDistributionItem(
                concept_name=name,
                question_counts=counts,
            )
        )
    return ConceptQuestionTypeDistribution(distribution=distribution)


# ============================================================================
# MOCK GEMINI CLIENT (for integration tests)
# ============================================================================


class MockParsedResponse:
    """Mock for response.parsed attribute."""

    def __init__(self, parsed_obj: Any):
        self._parsed = parsed_obj

    @property
    def parsed(self):
        return self._parsed


class MockQuestionsResponse:
    """Mock for questions response with .questions attribute."""

    def __init__(self, questions: list):
        self.questions = questions


class MockGeminiModels:
    """Mock for gemini_client.aio.models."""

    def _parse_requested_types(self, contents_str: str) -> dict[str, int]:
        """Parse requested question types from the distribution prompt."""
        import re
        
        requested = {}
        
        # Try to parse type counts from distribution prompt
        # The prompt typically contains something like: 'mcq4': 2, 'true_false': 1
        type_patterns = [
            ("mcq4", r"'mcq4'\s*:\s*(\d+)"),
            ("msq4", r"'msq4'\s*:\s*(\d+)"),
            ("fill_in_the_blank", r"'fill_in_the_blank'\s*:\s*(\d+)"),
            ("true_false", r"'true_false'\s*:\s*(\d+)"),
            ("short_answer", r"'short_answer'\s*:\s*(\d+)"),
            ("long_answer", r"'long_answer'\s*:\s*(\d+)"),
        ]
        
        for qtype, pattern in type_patterns:
            match = re.search(pattern, contents_str)
            if match:
                count = int(match.group(1))
                if count > 0:
                    requested[qtype] = count
        
        return requested if requested else {"mcq4": 2}

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

        # Handle distribution schema
        if schema == ConceptQuestionTypeDistribution or "distribution" in schema_name.lower():
            concept_names = ["Newton's Laws of Motion", "Kinetic Energy"]
            requested_types = self._parse_requested_types(str(contents))
            return MockParsedResponse(create_mock_distribution(concept_names, requested_types))

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

    def __init__(self, *args, **kwargs):
        # Accept any arguments (like api_key) but ignore them
        self.aio = MockAioNamespace()


# ============================================================================
# GEMINI MOCK FIXTURE (auto-applied unless --gemini-live)
# ============================================================================


@pytest.fixture(autouse=True)
def mock_gemini_client(use_live_gemini):
    """
    Automatically patch genai.Client for all integration tests unless --gemini-live is used.
    
    This patches at the module level where genai.Client is instantiated.
    """
    if use_live_gemini:
        # Use real Gemini API
        yield
    else:
        # Patch genai.Client in all qgen modules
        with patch("api.v1.qgen.question_generator.genai.Client", MockGeminiClient), \
             patch("api.v1.qgen.auto_correct_question.genai.Client", MockGeminiClient), \
             patch("api.v1.qgen.regenerate_question.genai.Client", MockGeminiClient), \
             patch("api.v1.qgen.regenerate_question_with_prompt.genai.Client", MockGeminiClient):
            yield


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def _get_session_access_token(auth_response) -> str | None:
    """Extract access_token from supabase-py auth response across versions."""
    session = getattr(auth_response, "session", None)
    if session is None and isinstance(auth_response, dict):
        session = auth_response.get("session")

    if session is None:
        return None

    token = getattr(session, "access_token", None)
    if token is None and isinstance(session, dict):
        token = session.get("access_token")

    return token


def _get_user_id(auth_response) -> str | None:
    """Extract user id from supabase-py auth response."""
    user = getattr(auth_response, "user", None)
    if user is None and isinstance(auth_response, dict):
        user = auth_response.get("user")

    if user is None:
        return None

    user_id = getattr(user, "id", None)
    if user_id is None and isinstance(user, dict):
        user_id = user.get("id")

    return user_id


# ============================================================================
# ENVIRONMENT FIXTURES
# ============================================================================


@pytest.fixture(scope="session")
def env(request) -> Dict[str, str]:
    """
    Load and validate required environment variables for integration tests.
    
    GEMINI_API_KEY is only required when --gemini-live flag is used.
    """
    load_dotenv()
    
    use_live_gemini = request.config.getoption("--gemini-live", default=False)

    supabase_url = os.getenv("SUPABASE_URL")
    supabase_anon_key = os.getenv("SUPABASE_ANON_KEY")
    supabase_service_key = os.getenv("SUPABASE_SERVICE_KEY")
    test_user_email = os.getenv("TEST_USER_EMAIL")
    test_user_password = os.getenv("TEST_USER_PASSWORD")
    gemini_api_key = os.getenv("GEMINI_API_KEY")

    # Base required vars (always needed for Supabase)
    required_vars = [
        ("SUPABASE_URL", supabase_url),
        ("SUPABASE_ANON_KEY", supabase_anon_key),
        ("SUPABASE_SERVICE_KEY", supabase_service_key),
        ("TEST_USER_EMAIL", test_user_email),
        ("TEST_USER_PASSWORD", test_user_password),
    ]
    
    # GEMINI_API_KEY only required with --gemini-live
    if use_live_gemini:
        required_vars.append(("GEMINI_API_KEY", gemini_api_key))

    missing = [name for name, value in required_vars if not value]
    if missing:
        pytest.skip("Missing env vars for integration tests: " + ", ".join(missing))

    return {
        "SUPABASE_URL": supabase_url,
        "SUPABASE_ANON_KEY": supabase_anon_key,
        "SUPABASE_SERVICE_KEY": supabase_service_key,
        "TEST_USER_EMAIL": test_user_email,
        "TEST_USER_PASSWORD": test_user_password,
        "GEMINI_API_KEY": gemini_api_key or "mock-api-key",  # Provide dummy value for mocks
    }


# ============================================================================
# SUPABASE CLIENT FIXTURES
# ============================================================================


@pytest.fixture(scope="session")
def service_supabase_client(env: Dict[str, str]) -> Client:
    """
    Create a Supabase client with service role key.
    Used for test data setup/teardown operations.
    """
    return create_client(env["SUPABASE_URL"], env["SUPABASE_SERVICE_KEY"])


@pytest.fixture(scope="session")
def auth_session(env: Dict[str, str]) -> Dict[str, Any]:
    """
    Authenticate as test user and return session info.
    """
    client = create_client(env["SUPABASE_URL"], env["SUPABASE_ANON_KEY"])
    auth_response = client.auth.sign_in_with_password(
        {
            "email": env["TEST_USER_EMAIL"],
            "password": env["TEST_USER_PASSWORD"],
        }
    )

    token = _get_session_access_token(auth_response)
    user_id = _get_user_id(auth_response)

    if not token:
        pytest.fail("Failed to get access token from Supabase sign-in")

    if not user_id:
        pytest.fail("Failed to get user ID from Supabase sign-in")

    return {
        "access_token": token,
        "user_id": user_id,
    }


# ============================================================================
# FASTAPI TEST CLIENT FIXTURES
# ============================================================================


@pytest.fixture(scope="session")
def app():
    """
    Create the FastAPI application instance.
    """
    return create_app()


@pytest.fixture(scope="session")
def test_client(app, auth_session: Dict[str, Any]) -> TestClient:
    """
    Create a TestClient with authentication headers.
    """
    client = TestClient(app)
    # Set default headers for all requests
    client.headers["Authorization"] = f"Bearer {auth_session['access_token']}"
    return client


@pytest.fixture
def unauthenticated_test_client(app) -> TestClient:
    """
    Create a TestClient without authentication headers.
    """
    return TestClient(app)


# ============================================================================
# TEST DATA FIXTURES
# ============================================================================


@pytest.fixture(scope="module")
def test_topic_id(service_supabase_client: Client) -> Generator[str, None, None]:
    """
    Get or create a test topic for concept creation.
    We need a valid topic_id since concepts require it.
    """
    # First, try to get an existing topic
    response = service_supabase_client.table("topics").select("id").limit(1).execute()

    if response.data and len(response.data) > 0:
        yield response.data[0]["id"]
    else:
        # If no topics exist, we need to create the hierarchy:
        # board -> school_class -> subject -> chapter -> topic

        # Check for existing board
        board_resp = (
            service_supabase_client.table("boards").select("id").limit(1).execute()
        )
        if board_resp.data:
            board_id = board_resp.data[0]["id"]
        else:
            board_id = str(uuid.uuid4())
            service_supabase_client.table("boards").insert(
                {"id": board_id, "name": "Test Board"}
            ).execute()

        # Check for existing school_class
        class_resp = (
            service_supabase_client.table("school_classes")
            .select("id")
            .limit(1)
            .execute()
        )
        if class_resp.data:
            class_id = class_resp.data[0]["id"]
        else:
            class_id = str(uuid.uuid4())
            service_supabase_client.table("school_classes").insert(
                {
                    "id": class_id,
                    "name": "Test Class",
                    "board_id": board_id,
                    "position": 1,
                }
            ).execute()

        # Check for existing subject
        subject_resp = (
            service_supabase_client.table("subjects").select("id").limit(1).execute()
        )
        if subject_resp.data:
            subject_id = subject_resp.data[0]["id"]
        else:
            subject_id = str(uuid.uuid4())
            service_supabase_client.table("subjects").insert(
                {"id": subject_id, "name": "Test Subject", "school_class_id": class_id}
            ).execute()

        # Check for existing chapter
        chapter_resp = (
            service_supabase_client.table("chapters").select("id").limit(1).execute()
        )
        if chapter_resp.data:
            chapter_id = chapter_resp.data[0]["id"]
        else:
            chapter_id = str(uuid.uuid4())
            service_supabase_client.table("chapters").insert(
                {"id": chapter_id, "name": "Test Chapter", "subject_id": subject_id}
            ).execute()

        # Create topic
        topic_id = str(uuid.uuid4())
        service_supabase_client.table("topics").insert(
            {
                "id": topic_id,
                "name": "Test Topic",
                "chapter_id": chapter_id,
                "position": 1,
            }
        ).execute()

        yield topic_id

        # Cleanup: We won't delete the hierarchy to avoid breaking other tests


@pytest.fixture
def test_concepts(
    service_supabase_client: Client,
    test_topic_id: str,
) -> Generator[List[Dict[str, Any]], None, None]:
    """
    Create test concepts in Supabase and clean up after test.
    """
    concept_ids = [str(uuid.uuid4()), str(uuid.uuid4())]

    concepts_data = [
        {
            "id": concept_ids[0],
            "name": "Newton's Laws of Motion",
            "description": "The three fundamental laws describing the relationship between forces and motion.",
            "topic_id": test_topic_id,
            "page_number": 1,
        },
        {
            "id": concept_ids[1],
            "name": "Kinetic Energy",
            "description": "Energy possessed by an object due to its motion. Formula: KE = 1/2 * m * v^2.",
            "topic_id": test_topic_id,
            "page_number": 2,
        },
    ]

    # Insert concepts
    response = service_supabase_client.table("concepts").insert(concepts_data).execute()

    yield response.data

    # Cleanup: Delete test concepts
    service_supabase_client.table("concepts").delete().in_("id", concept_ids).execute()


@pytest.fixture
def test_activity(
    service_supabase_client: Client,
    auth_session: Dict[str, Any],
) -> Generator[Dict[str, Any], None, None]:
    """
    Create a test activity in Supabase and clean up after test.
    """
    activity_id = str(uuid.uuid4())
    user_id = auth_session["user_id"]

    activity_data = {
        "id": activity_id,
        "name": "Test Activity for Question Generation",
        "product_type": PublicProductTypeEnumEnum.QGEN.value,
        "user_id": user_id,
    }

    # Insert activity
    response = (
        service_supabase_client.table("activities").insert(activity_data).execute()
    )

    yield response.data[0]

    # Cleanup: First delete related data, then delete activity
    # Delete gen_questions_concepts_maps entries
    gen_questions = (
        service_supabase_client.table("gen_questions")
        .select("id")
        .eq("activity_id", activity_id)
        .execute()
    )

    if gen_questions.data:
        question_ids = [q["id"] for q in gen_questions.data]
        service_supabase_client.table("gen_questions_concepts_maps").delete().in_(
            "gen_question_id", question_ids
        ).execute()

        # Delete gen_questions
        service_supabase_client.table("gen_questions").delete().eq(
            "activity_id", activity_id
        ).execute()

    # Delete the activity
    service_supabase_client.table("activities").delete().eq("id", activity_id).execute()


@pytest.fixture
def test_bank_questions(
    service_supabase_client: Client,
    test_concepts: List[Dict[str, Any]],
) -> Generator[List[Dict[str, Any]], None, None]:
    """
    Create test bank questions (historical questions) for the concepts.
    These are used as reference data for question generation.
    """
    # Get a subject_id for the bank questions
    subject_resp = (
        service_supabase_client.table("subjects").select("id").limit(1).execute()
    )

    if not subject_resp.data:
        pytest.skip("No subjects available for bank questions")

    subject_id = subject_resp.data[0]["id"]

    question_ids = [str(uuid.uuid4()), str(uuid.uuid4())]
    concept_ids = [c["id"] for c in test_concepts]

    bank_questions_data = [
        {
            "id": question_ids[0],
            "question_text": "What is Newton's First Law of Motion?",
            "question_type": "mcq4",
            "option1": "Law of Inertia",
            "option2": "Law of Acceleration",
            "option3": "Law of Action-Reaction",
            "option4": "Law of Gravity",
            "correct_mcq_option": 1,
            "answer_text": "Law of Inertia",
            "explanation": "Newton's First Law states that an object at rest stays at rest.",
            "hardness_level": "easy",
            "marks": 1,
            "subject_id": subject_id,
        },
        {
            "id": question_ids[1],
            "question_text": "Calculate the kinetic energy of a 2kg object moving at 3 m/s.",
            "question_type": "short_answer",
            "answer_text": "KE = 1/2 * 2 * 3^2 = 9 Joules",
            "explanation": "Using the formula KE = 1/2 * m * v^2",
            "hardness_level": "medium",
            "marks": 2,
            "subject_id": subject_id,
        },
    ]

    # Insert bank questions
    response = (
        service_supabase_client.table("bank_questions")
        .insert(bank_questions_data)
        .execute()
    )

    # Create mappings between bank questions and concepts
    mappings_data = [
        {
            "id": str(uuid.uuid4()),
            "bank_question_id": question_ids[0],
            "concept_id": concept_ids[0],
        },
        {
            "id": str(uuid.uuid4()),
            "bank_question_id": question_ids[1],
            "concept_id": concept_ids[1],
        },
    ]

    service_supabase_client.table("bank_questions_concepts_maps").insert(
        mappings_data
    ).execute()

    yield response.data

    # Cleanup: Delete mappings first, then questions
    service_supabase_client.table("bank_questions_concepts_maps").delete().in_(
        "bank_question_id", question_ids
    ).execute()

    service_supabase_client.table("bank_questions").delete().in_(
        "id", question_ids
    ).execute()

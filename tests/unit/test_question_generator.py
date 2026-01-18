"""
Unit tests for question generation logic functions.

These tests use a real Gemini client with mock data to validate
the generate_distribution and generate_questions_for_distribution functions.
"""

import os
import uuid
from typing import Dict, List

import pytest
from dotenv import load_dotenv
import google.genai as genai

from api.v1.qgen.question_generator import (
    generate_distribution,
    generate_questions_for_distribution,
    TotalQuestionTypeCounts,
    ConceptQuestionTypeDistribution,
    ConceptDistributionItem,
    QuestionTypeDistribution,
    PublicHardnessLevelEnumEnum,
    QUESTION_TYPE_TO_ENUM,
)


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture(scope="session")
def gemini_client() -> genai.Client:
    """
    Create a real Gemini client using API key from environment.
    """
    load_dotenv()

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        pytest.skip("GEMINI_API_KEY not set in environment")

    return genai.Client(api_key=api_key)


@pytest.fixture
def mock_concepts() -> List[Dict[str, str]]:
    """
    Mock concept data matching the expected structure from Supabase.
    """
    return [
        {
            "id": "550e8400-e29b-41d4-a716-446655440001",
            "name": "Newton's Laws of Motion",
            "description": "The three fundamental laws that describe the relationship between forces and motion. First law: inertia. Second law: F=ma. Third law: action-reaction.",
        },
        {
            "id": "550e8400-e29b-41d4-a716-446655440002",
            "name": "Kinetic Energy",
            "description": "Energy possessed by an object due to its motion. Formula: KE = 1/2 * m * v^2 where m is mass and v is velocity.",
        },
    ]


@pytest.fixture
def mock_concepts_dict(mock_concepts: List[Dict[str, str]]) -> Dict[str, str]:
    """
    Create concept name to description mapping.
    """
    return {concept["name"]: concept["description"] for concept in mock_concepts}


@pytest.fixture
def mock_concepts_name_to_id(mock_concepts: List[Dict[str, str]]) -> Dict[str, str]:
    """
    Create concept name to ID mapping.
    """
    return {concept["name"]: concept["id"] for concept in mock_concepts}


@pytest.fixture
def mock_old_questions() -> List[dict]:
    """
    Mock historical questions from bank_questions table.
    """
    return [
        {
            "id": "660e8400-e29b-41d4-a716-446655440001",
            "question_text": "What is Newton's First Law of Motion?",
            "question_type": "mcq4",
            "option1": "Law of Inertia",
            "option2": "Law of Acceleration",
            "option3": "Law of Action-Reaction",
            "option4": "Law of Gravity",
            "correct_mcq_option": 1,
            "answer_text": None,
            "explanation": "Newton's First Law states that an object at rest stays at rest and an object in motion stays in motion unless acted upon by an external force.",
            "hardness_level": "easy",
            "marks": 1,
        },
        {
            "id": "660e8400-e29b-41d4-a716-446655440002",
            "question_text": "Calculate the kinetic energy of a 2kg object moving at 3 m/s.",
            "question_type": "short_answer",
            "option1": None,
            "option2": None,
            "option3": None,
            "option4": None,
            "correct_mcq_option": None,
            "answer_text": "KE = 1/2 * 2 * 3^2 = 9 Joules",
            "explanation": "Using the formula KE = 1/2 * m * v^2",
            "hardness_level": "medium",
            "marks": 2,
        },
    ]


@pytest.fixture
def mock_question_type_counts() -> TotalQuestionTypeCounts:
    """
    Mock question type counts for distribution.
    """
    return TotalQuestionTypeCounts(
        total_mcq4s=2,
        total_msq4s=0,
        total_fill_in_the_blanks=1,
        total_true_falses=1,
        total_short_answers=0,
        total_long_answers=0,
    )


@pytest.fixture
def mock_activity_id() -> uuid.UUID:
    """
    Mock activity ID.
    """
    return uuid.UUID("770e8400-e29b-41d4-a716-446655440001")


# ============================================================================
# TESTS FOR generate_distribution
# ============================================================================


class TestGenerateDistribution:
    """Tests for the generate_distribution function."""

    def test_returns_concept_question_type_distribution(
        self,
        gemini_client: genai.Client,
        mock_question_type_counts: TotalQuestionTypeCounts,
        mock_concepts: List[Dict[str, str]],
        mock_old_questions: List[dict],
    ):
        """
        Test that generate_distribution returns a valid ConceptQuestionTypeDistribution.
        """
        result = generate_distribution(
            gemini_client=gemini_client,
            question_type_counts=mock_question_type_counts,
            concepts=mock_concepts,
            old_questions=mock_old_questions,
        )

        # Verify return type
        assert isinstance(result, ConceptQuestionTypeDistribution)
        assert hasattr(result, "distribution")
        assert isinstance(result.distribution, list)

    def test_distribution_contains_concept_names(
        self,
        gemini_client: genai.Client,
        mock_question_type_counts: TotalQuestionTypeCounts,
        mock_concepts: List[Dict[str, str]],
        mock_old_questions: List[dict],
    ):
        """
        Test that the distribution concept names are from input.
        """
        result = generate_distribution(
            gemini_client=gemini_client,
            question_type_counts=mock_question_type_counts,
            concepts=mock_concepts,
            old_questions=mock_old_questions,
        )

        concept_names = {c["name"] for c in mock_concepts}

        # At least one concept should be in the distribution
        assert len(result.distribution) > 0

        # All concept names in distribution should be from our concepts
        for item in result.distribution:
            assert (
                item.concept_name in concept_names
            ), f"Unexpected concept in distribution: {item.concept_name}"

    def test_distribution_values_are_question_type_distributions(
        self,
        gemini_client: genai.Client,
        mock_question_type_counts: TotalQuestionTypeCounts,
        mock_concepts: List[Dict[str, str]],
        mock_old_questions: List[dict],
    ):
        """
        Test that each item in the distribution has valid QuestionTypeDistribution.
        """
        result = generate_distribution(
            gemini_client=gemini_client,
            question_type_counts=mock_question_type_counts,
            concepts=mock_concepts,
            old_questions=mock_old_questions,
        )

        for item in result.distribution:
            assert isinstance(item, ConceptDistributionItem)
            assert isinstance(item.question_counts, QuestionTypeDistribution)
            distribution = item.question_counts
            assert hasattr(distribution, "mcq4")
            assert hasattr(distribution, "msq4")
            assert hasattr(distribution, "fill_in_the_blank")
            assert hasattr(distribution, "true_false")
            assert hasattr(distribution, "short_answer")
            assert hasattr(distribution, "long_answer")

            # All counts should be non-negative
            assert distribution.mcq4 >= 0
            assert distribution.msq4 >= 0
            assert distribution.fill_in_the_blank >= 0
            assert distribution.true_false >= 0
            assert distribution.short_answer >= 0
            assert distribution.long_answer >= 0

    def test_distribution_respects_total_counts(
        self,
        gemini_client: genai.Client,
        mock_question_type_counts: TotalQuestionTypeCounts,
        mock_concepts: List[Dict[str, str]],
        mock_old_questions: List[dict],
    ):
        """
        Test that the sum of distributed questions matches (or approximates) the total requested.
        """
        result = generate_distribution(
            gemini_client=gemini_client,
            question_type_counts=mock_question_type_counts,
            concepts=mock_concepts,
            old_questions=mock_old_questions,
        )

        total_mcq4 = sum(item.question_counts.mcq4 for item in result.distribution)
        total_fill_in_blank = sum(
            item.question_counts.fill_in_the_blank for item in result.distribution
        )
        total_true_false = sum(
            item.question_counts.true_false for item in result.distribution
        )

        # The totals should match the requested counts
        assert total_mcq4 == mock_question_type_counts.total_mcq4s
        assert total_fill_in_blank == mock_question_type_counts.total_fill_in_the_blanks
        assert total_true_false == mock_question_type_counts.total_true_falses

    def test_distribution_with_instructions(
        self,
        gemini_client: genai.Client,
        mock_question_type_counts: TotalQuestionTypeCounts,
        mock_concepts: List[Dict[str, str]],
        mock_old_questions: List[dict],
    ):
        """
        Test that generate_distribution accepts and uses instructions parameter.
        """
        instructions = "Focus on Newton's Laws more than Kinetic Energy."

        result = generate_distribution(
            gemini_client=gemini_client,
            question_type_counts=mock_question_type_counts,
            concepts=mock_concepts,
            old_questions=mock_old_questions,
            instructions=instructions,
        )

        # Verify return type is still valid
        assert isinstance(result, ConceptQuestionTypeDistribution)
        assert hasattr(result, "distribution")
        assert isinstance(result.distribution, list)
        assert len(result.distribution) > 0

    def test_distribution_with_empty_instructions(
        self,
        gemini_client: genai.Client,
        mock_question_type_counts: TotalQuestionTypeCounts,
        mock_concepts: List[Dict[str, str]],
        mock_old_questions: List[dict],
    ):
        """
        Test that generate_distribution works with empty string instructions.
        """
        result = generate_distribution(
            gemini_client=gemini_client,
            question_type_counts=mock_question_type_counts,
            concepts=mock_concepts,
            old_questions=mock_old_questions,
            instructions="",
        )

        # Should work normally with empty instructions
        assert isinstance(result, ConceptQuestionTypeDistribution)
        assert len(result.distribution) > 0

    def test_distribution_with_none_instructions(
        self,
        gemini_client: genai.Client,
        mock_question_type_counts: TotalQuestionTypeCounts,
        mock_concepts: List[Dict[str, str]],
        mock_old_questions: List[dict],
    ):
        """
        Test that generate_distribution works with None instructions (default).
        """
        result = generate_distribution(
            gemini_client=gemini_client,
            question_type_counts=mock_question_type_counts,
            concepts=mock_concepts,
            old_questions=mock_old_questions,
            instructions=None,
        )

        # Should work normally with None instructions
        assert isinstance(result, ConceptQuestionTypeDistribution)
        assert len(result.distribution) > 0


# ============================================================================
# TESTS FOR generate_questions_for_distribution
# ============================================================================


class TestGenerateQuestionsForDistribution:
    """Tests for the generate_questions_for_distribution function."""

    @pytest.fixture
    def mock_distribution(
        self, mock_concepts: List[Dict[str, str]]
    ) -> ConceptQuestionTypeDistribution:
        """
        Create a mock distribution for testing question generation.
        """
        return ConceptQuestionTypeDistribution(
            distribution=[
                ConceptDistributionItem(
                    concept_name=mock_concepts[0]["name"],
                    question_counts=QuestionTypeDistribution(
                        mcq4=1,
                        msq4=0,
                        fill_in_the_blank=0,
                        true_false=1,
                        short_answer=0,
                        long_answer=0,
                    ),
                ),
                ConceptDistributionItem(
                    concept_name=mock_concepts[1]["name"],
                    question_counts=QuestionTypeDistribution(
                        mcq4=1,
                        msq4=0,
                        fill_in_the_blank=0,
                        true_false=0,
                        short_answer=0,
                        long_answer=0,
                    ),
                ),
            ]
        )

    def test_returns_list_of_dicts(
        self,
        gemini_client: genai.Client,
        mock_distribution: ConceptQuestionTypeDistribution,
        mock_concepts_dict: Dict[str, str],
        mock_concepts_name_to_id: Dict[str, str],
        mock_old_questions: List[dict],
        mock_activity_id: uuid.UUID,
    ):
        """
        Test that generate_questions_for_distribution returns a list of dicts.
        """
        result = generate_questions_for_distribution(
            gemini_client=gemini_client,
            distribution=mock_distribution,
            concepts_dict=mock_concepts_dict,
            concepts_name_to_id=mock_concepts_name_to_id,
            old_questions=mock_old_questions,
            activity_id=mock_activity_id,
        )

        assert isinstance(result, list)
        assert len(result) > 0

        for item in result:
            assert isinstance(item, dict)
            assert "question" in item
            assert "concept_id" in item

    def test_question_dict_has_required_fields(
        self,
        gemini_client: genai.Client,
        mock_distribution: ConceptQuestionTypeDistribution,
        mock_concepts_dict: Dict[str, str],
        mock_concepts_name_to_id: Dict[str, str],
        mock_old_questions: List[dict],
        mock_activity_id: uuid.UUID,
    ):
        """
        Test that each generated question dict has required fields.
        """
        result = generate_questions_for_distribution(
            gemini_client=gemini_client,
            distribution=mock_distribution,
            concepts_dict=mock_concepts_dict,
            concepts_name_to_id=mock_concepts_name_to_id,
            old_questions=mock_old_questions,
            activity_id=mock_activity_id,
        )

        for item in result:
            question = item["question"]

            # Required fields that should be present
            assert "activity_id" in question
            assert "question_type" in question
            assert "hardness_level" in question
            assert "marks" in question

            # Verify activity_id matches
            assert question["activity_id"] == str(mock_activity_id)

            # Verify question_type is a valid enum
            assert question["question_type"] in QUESTION_TYPE_TO_ENUM.values()

    def test_concept_ids_are_valid(
        self,
        gemini_client: genai.Client,
        mock_distribution: ConceptQuestionTypeDistribution,
        mock_concepts_dict: Dict[str, str],
        mock_concepts_name_to_id: Dict[str, str],
        mock_old_questions: List[dict],
        mock_activity_id: uuid.UUID,
    ):
        """
        Test that concept IDs in results match our input concepts.
        """
        result = generate_questions_for_distribution(
            gemini_client=gemini_client,
            distribution=mock_distribution,
            concepts_dict=mock_concepts_dict,
            concepts_name_to_id=mock_concepts_name_to_id,
            old_questions=mock_old_questions,
            activity_id=mock_activity_id,
        )

        valid_concept_ids = set(mock_concepts_name_to_id.values())

        for item in result:
            assert item["concept_id"] in valid_concept_ids

    def test_generates_correct_number_of_questions(
        self,
        gemini_client: genai.Client,
        mock_distribution: ConceptQuestionTypeDistribution,
        mock_concepts_dict: Dict[str, str],
        mock_concepts_name_to_id: Dict[str, str],
        mock_old_questions: List[dict],
        mock_activity_id: uuid.UUID,
    ):
        """
        Test that the number of generated questions matches the distribution.
        """
        result = generate_questions_for_distribution(
            gemini_client=gemini_client,
            distribution=mock_distribution,
            concepts_dict=mock_concepts_dict,
            concepts_name_to_id=mock_concepts_name_to_id,
            old_questions=mock_old_questions,
            activity_id=mock_activity_id,
        )

        # Calculate expected total from distribution
        expected_total = sum(
            item.question_counts.mcq4
            + item.question_counts.msq4
            + item.question_counts.fill_in_the_blank
            + item.question_counts.true_false
            + item.question_counts.short_answer
            + item.question_counts.long_answer
            for item in mock_distribution.distribution
        )

        assert len(result) == expected_total

    def test_uses_default_hardness_level(
        self,
        gemini_client: genai.Client,
        mock_distribution: ConceptQuestionTypeDistribution,
        mock_concepts_dict: Dict[str, str],
        mock_concepts_name_to_id: Dict[str, str],
        mock_old_questions: List[dict],
        mock_activity_id: uuid.UUID,
    ):
        """
        Test that default hardness level is applied.
        """
        result = generate_questions_for_distribution(
            gemini_client=gemini_client,
            distribution=mock_distribution,
            concepts_dict=mock_concepts_dict,
            concepts_name_to_id=mock_concepts_name_to_id,
            old_questions=mock_old_questions,
            activity_id=mock_activity_id,
        )

        for item in result:
            assert (
                item["question"]["hardness_level"] == PublicHardnessLevelEnumEnum.MEDIUM
            )

    def test_custom_hardness_level(
        self,
        gemini_client: genai.Client,
        mock_distribution: ConceptQuestionTypeDistribution,
        mock_concepts_dict: Dict[str, str],
        mock_concepts_name_to_id: Dict[str, str],
        mock_old_questions: List[dict],
        mock_activity_id: uuid.UUID,
    ):
        """
        Test that custom hardness level is applied when specified.
        """
        custom_hardness = PublicHardnessLevelEnumEnum.HARD

        result = generate_questions_for_distribution(
            gemini_client=gemini_client,
            distribution=mock_distribution,
            concepts_dict=mock_concepts_dict,
            concepts_name_to_id=mock_concepts_name_to_id,
            old_questions=mock_old_questions,
            activity_id=mock_activity_id,
            default_hardness=custom_hardness,
        )

        for item in result:
            assert item["question"]["hardness_level"] == custom_hardness

    def test_custom_marks(
        self,
        gemini_client: genai.Client,
        mock_distribution: ConceptQuestionTypeDistribution,
        mock_concepts_dict: Dict[str, str],
        mock_concepts_name_to_id: Dict[str, str],
        mock_old_questions: List[dict],
        mock_activity_id: uuid.UUID,
    ):
        """
        Test that custom marks value is applied when specified.
        """
        custom_marks = 5

        result = generate_questions_for_distribution(
            gemini_client=gemini_client,
            distribution=mock_distribution,
            concepts_dict=mock_concepts_dict,
            concepts_name_to_id=mock_concepts_name_to_id,
            old_questions=mock_old_questions,
            activity_id=mock_activity_id,
            default_marks=custom_marks,
        )

        for item in result:
            assert item["question"]["marks"] == custom_marks

    def test_mcq4_questions_have_options(
        self,
        gemini_client: genai.Client,
        mock_concepts_dict: Dict[str, str],
        mock_concepts_name_to_id: Dict[str, str],
        mock_concepts: List[Dict[str, str]],
        mock_old_questions: List[dict],
        mock_activity_id: uuid.UUID,
    ):
        """
        Test that MCQ4 questions have option fields.
        """
        # Create a distribution with only MCQ4 questions
        mcq_only_distribution = ConceptQuestionTypeDistribution(
            distribution=[
                ConceptDistributionItem(
                    concept_name=mock_concepts[0]["name"],
                    question_counts=QuestionTypeDistribution(
                        mcq4=1,
                        msq4=0,
                        fill_in_the_blank=0,
                        true_false=0,
                        short_answer=0,
                        long_answer=0,
                    ),
                ),
            ]
        )

        result = generate_questions_for_distribution(
            gemini_client=gemini_client,
            distribution=mcq_only_distribution,
            concepts_dict=mock_concepts_dict,
            concepts_name_to_id=mock_concepts_name_to_id,
            old_questions=mock_old_questions,
            activity_id=mock_activity_id,
        )

        assert len(result) == 1
        question = result[0]["question"]

        # MCQ4 should have options and correct_mcq_option
        assert "option1" in question
        assert "option2" in question
        assert "option3" in question
        assert "option4" in question
        assert "correct_mcq_option" in question

    def test_skips_unknown_concepts(
        self,
        gemini_client: genai.Client,
        mock_concepts_dict: Dict[str, str],
        mock_old_questions: List[dict],
        mock_activity_id: uuid.UUID,
    ):
        """
        Test that unknown concepts in distribution are skipped.
        """
        # Create a distribution with an unknown concept
        distribution_with_unknown = ConceptQuestionTypeDistribution(
            distribution=[
                ConceptDistributionItem(
                    concept_name="Unknown Concept XYZ",
                    question_counts=QuestionTypeDistribution(
                        mcq4=1,
                        msq4=0,
                        fill_in_the_blank=0,
                        true_false=0,
                        short_answer=0,
                        long_answer=0,
                    ),
                ),
            ]
        )

        # Empty concepts_name_to_id means no valid concepts
        result = generate_questions_for_distribution(
            gemini_client=gemini_client,
            distribution=distribution_with_unknown,
            concepts_dict=mock_concepts_dict,
            concepts_name_to_id={},  # No valid concept IDs
            old_questions=mock_old_questions,
            activity_id=mock_activity_id,
        )

        # Should return empty list since concept ID not found
        assert len(result) == 0

    def test_generates_questions_with_instructions(
        self,
        gemini_client: genai.Client,
        mock_distribution: ConceptQuestionTypeDistribution,
        mock_concepts_dict: Dict[str, str],
        mock_concepts_name_to_id: Dict[str, str],
        mock_old_questions: List[dict],
        mock_activity_id: uuid.UUID,
    ):
        """
        Test that generate_questions_for_distribution accepts and uses instructions.
        """
        instructions = "Make questions focus on practical applications."

        result = generate_questions_for_distribution(
            gemini_client=gemini_client,
            distribution=mock_distribution,
            concepts_dict=mock_concepts_dict,
            concepts_name_to_id=mock_concepts_name_to_id,
            old_questions=mock_old_questions,
            activity_id=mock_activity_id,
            instructions=instructions,
        )

        # Should still return valid results
        assert isinstance(result, list)
        assert len(result) > 0

        for item in result:
            assert isinstance(item, dict)
            assert "question" in item
            assert "concept_id" in item

    def test_generates_questions_with_empty_instructions(
        self,
        gemini_client: genai.Client,
        mock_distribution: ConceptQuestionTypeDistribution,
        mock_concepts_dict: Dict[str, str],
        mock_concepts_name_to_id: Dict[str, str],
        mock_old_questions: List[dict],
        mock_activity_id: uuid.UUID,
    ):
        """
        Test that generate_questions_for_distribution works with empty instructions.
        """
        result = generate_questions_for_distribution(
            gemini_client=gemini_client,
            distribution=mock_distribution,
            concepts_dict=mock_concepts_dict,
            concepts_name_to_id=mock_concepts_name_to_id,
            old_questions=mock_old_questions,
            activity_id=mock_activity_id,
            instructions="",
        )

        # Should work normally
        assert isinstance(result, list)
        assert len(result) > 0

    def test_generates_questions_with_none_instructions(
        self,
        gemini_client: genai.Client,
        mock_distribution: ConceptQuestionTypeDistribution,
        mock_concepts_dict: Dict[str, str],
        mock_concepts_name_to_id: Dict[str, str],
        mock_old_questions: List[dict],
        mock_activity_id: uuid.UUID,
    ):
        """
        Test that generate_questions_for_distribution works with None instructions.
        """
        result = generate_questions_for_distribution(
            gemini_client=gemini_client,
            distribution=mock_distribution,
            concepts_dict=mock_concepts_dict,
            concepts_name_to_id=mock_concepts_name_to_id,
            old_questions=mock_old_questions,
            activity_id=mock_activity_id,
            instructions=None,
        )

        # Should work normally
        assert isinstance(result, list)
        assert len(result) > 0

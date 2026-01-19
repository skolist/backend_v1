"""
Unit tests for question generation logic functions with batchification.

These tests validate the batchification-based question generation logic,
including the build_batches_end_to_end function and generate_questions_for_batches.
"""

import uuid
from typing import Dict, List

import pytest
import google.genai as genai

from api.v1.qgen.question_generator import (
    generate_questions_for_batches,
    extract_question_type_counts_dict,
    extract_difficulty_percentages,
    generate_questions_prompt,
    GenerateQuestionsRequest,
    QuestionConfig,
    QuestionTypeConfig,
    DifficultyDistribution,
    QUESTION_TYPE_TO_ENUM,
)
from api.v1.qgen.utils.batchification import (
    build_batches_end_to_end,
    Batch,
    _dedupe_preserve_order,
    _normalize_weights,
    _chunk_questions,
    _expand_concepts_to_slots,
    _largest_remainder_apportion,
)
from supabase_dir import PublicHardnessLevelEnumEnum


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def mock_concepts() -> List[Dict[str, str]]:
    """
    Mock concept data matching the expected structure from Supabase.
    """
    return [
        {
            "id": "550e8400-e29b-41d4-a716-446655440001",
            "name": "Newton's Laws of Motion",
            "description": "The three fundamental laws that describe the relationship between forces and motion.",
        },
        {
            "id": "550e8400-e29b-41d4-a716-446655440002",
            "name": "Kinetic Energy",
            "description": "Energy possessed by an object due to its motion. Formula: KE = 1/2 * m * v^2.",
        },
        {
            "id": "550e8400-e29b-41d4-a716-446655440003",
            "name": "Potential Energy",
            "description": "Energy stored in an object due to its position or configuration.",
        },
    ]


@pytest.fixture
def mock_concepts_dict(mock_concepts: List[Dict[str, str]]) -> Dict[str, str]:
    """Create concept name to description mapping."""
    return {concept["name"]: concept["description"] for concept in mock_concepts}


@pytest.fixture
def mock_concepts_name_to_id(mock_concepts: List[Dict[str, str]]) -> Dict[str, str]:
    """Create concept name to ID mapping."""
    return {concept["name"]: concept["id"] for concept in mock_concepts}


@pytest.fixture
def mock_old_questions() -> List[dict]:
    """Mock historical questions from bank_questions table."""
    return [
        {
            "id": "660e8400-e29b-41d4-a716-446655440001",
            "question_text": "What is Newton's First Law of Motion?",
            "question_type": "mcq4",
            "hardness_level": "easy",
        },
    ]


@pytest.fixture
def mock_activity_id() -> uuid.UUID:
    """Mock activity ID."""
    return uuid.UUID("770e8400-e29b-41d4-a716-446655440001")


# ============================================================================
# TESTS FOR BATCHIFICATION HELPER FUNCTIONS
# ============================================================================


class TestDedupePreserveOrder:
    """Tests for _dedupe_preserve_order function."""

    def test_removes_duplicates_preserves_order(self):
        """Test that duplicates are removed while preserving order."""
        items = ["a", "b", "a", "c", "b", "d"]
        result = _dedupe_preserve_order(items)
        assert result == ["a", "b", "c", "d"]

    def test_handles_empty_list(self):
        """Test with empty list."""
        result = _dedupe_preserve_order([])
        assert result == []

    def test_strips_whitespace(self):
        """Test that whitespace is stripped."""
        items = ["  a  ", "b", " a", "c "]
        result = _dedupe_preserve_order(items)
        assert result == ["a", "b", "c"]

    def test_ignores_empty_strings(self):
        """Test that empty strings are ignored."""
        items = ["a", "", "b", "   ", "c"]
        result = _dedupe_preserve_order(items)
        assert result == ["a", "b", "c"]


class TestNormalizeWeights:
    """Tests for _normalize_weights function."""

    def test_normalizes_weights_to_sum_one(self):
        """Test that weights are normalized to sum to 1."""
        weights = {"easy": 50, "medium": 30, "hard": 20}
        result = _normalize_weights(weights)
        assert abs(sum(result.values()) - 1.0) < 0.0001
        assert result["easy"] == 0.5
        assert result["medium"] == 0.3
        assert result["hard"] == 0.2

    def test_raises_error_for_all_zero_weights(self):
        """Test that error is raised when all weights are zero."""
        with pytest.raises(ValueError, match="All weights are zero"):
            _normalize_weights({"easy": 0, "medium": 0, "hard": 0})

    def test_ignores_negative_weights(self):
        """Test that negative weights are filtered out."""
        weights = {"easy": 100, "medium": -10, "hard": 0}
        result = _normalize_weights(weights)
        assert result["easy"] == 1.0


class TestChunkQuestions:
    """Tests for _chunk_questions function."""

    def test_chunks_correctly(self):
        """Test that questions are chunked correctly."""
        assert _chunk_questions(7, 3) == [3, 3, 1]
        assert _chunk_questions(6, 3) == [3, 3]
        assert _chunk_questions(2, 3) == [2]
        assert _chunk_questions(0, 3) == []

    def test_raises_error_for_negative_n(self):
        """Test that error is raised for negative n."""
        with pytest.raises(ValueError, match="n must be >= 0"):
            _chunk_questions(-1, 3)


class TestExpandConceptsToSlots:
    """Tests for _expand_concepts_to_slots function."""

    def test_expands_concepts_when_fewer_than_slots(self):
        """Test that concepts are repeated when fewer than slots."""
        import random

        rng = random.Random(42)
        concepts = ["a", "b"]
        result = _expand_concepts_to_slots(
            concepts, slots=5, rng=rng, shuffle_each_cycle=False
        )
        assert len(result) == 5
        assert all(c in ["a", "b"] for c in result)

    def test_truncates_concepts_when_more_than_slots(self):
        """Test that concepts are truncated when more than slots."""
        import random

        rng = random.Random(42)
        concepts = ["a", "b", "c", "d", "e"]
        result = _expand_concepts_to_slots(concepts, slots=3, rng=rng)
        assert len(result) == 3

    def test_raises_error_for_empty_concepts(self):
        """Test that error is raised for empty concepts."""
        import random

        rng = random.Random(42)
        with pytest.raises(ValueError, match="concepts must be non-empty"):
            _expand_concepts_to_slots([], slots=3, rng=rng)

    def test_returns_empty_for_zero_slots(self):
        """Test that empty list is returned for zero slots."""
        import random

        rng = random.Random(42)
        result = _expand_concepts_to_slots(["a", "b"], slots=0, rng=rng)
        assert result == []


class TestLargestRemainderApportion:
    """Tests for _largest_remainder_apportion function."""

    def test_apportions_correctly(self):
        """Test that apportionment sums to total."""
        keys = ["easy", "medium", "hard"]
        weights = {"easy": 0.5, "medium": 0.3, "hard": 0.2}
        result = _largest_remainder_apportion(10, keys, weights)
        assert sum(result.values()) == 10
        assert result["easy"] == 5
        assert result["medium"] == 3
        assert result["hard"] == 2

    def test_handles_zero_total(self):
        """Test with zero total."""
        keys = ["easy", "medium"]
        weights = {"easy": 0.5, "medium": 0.5}
        result = _largest_remainder_apportion(0, keys, weights)
        assert result == {"easy": 0, "medium": 0}

    def test_raises_error_for_negative_total(self):
        """Test that error is raised for negative total."""
        with pytest.raises(ValueError, match="total must be >= 0"):
            _largest_remainder_apportion(-1, ["a"], {"a": 1.0})


# ============================================================================
# TESTS FOR build_batches_end_to_end
# ============================================================================


class TestBuildBatchesEndToEnd:
    """Tests for the build_batches_end_to_end function."""

    def test_creates_batches_basic(self):
        """Test basic batch creation."""
        batches = build_batches_end_to_end(
            question_type_counts={"mcq4": 5},
            concepts=["Concept A", "Concept B"],
            difficulty_percent={"easy": 50, "medium": 50},
            custom_instruction="Test instruction",
            seed=42,
        )

        assert isinstance(batches, list)
        assert len(batches) > 0
        assert all(isinstance(b, Batch) for b in batches)
        assert sum(b.n_questions for b in batches) == 5

    def test_batches_respect_max_questions(self):
        """Test that batches don't exceed max_questions_per_batch."""
        batches = build_batches_end_to_end(
            question_type_counts={"mcq4": 10},
            concepts=["Concept A"],
            difficulty_percent={"easy": 100},
            custom_instruction=None,
            max_questions_per_batch=3,
            seed=42,
        )

        assert all(b.n_questions <= 3 for b in batches)

    def test_batches_have_at_least_one_concept(self):
        """Test that all batches have at least one concept."""
        batches = build_batches_end_to_end(
            question_type_counts={"mcq4": 5, "true_false": 3},
            concepts=["Concept A", "Concept B"],
            difficulty_percent={"easy": 30, "medium": 40, "hard": 30},
            custom_instruction=None,
            seed=42,
        )

        assert all(len(b.concepts) >= 1 for b in batches)

    def test_multiple_question_types(self):
        """Test with multiple question types."""
        batches = build_batches_end_to_end(
            question_type_counts={"mcq4": 3, "true_false": 2, "short_answer": 1},
            concepts=["Concept A", "Concept B"],
            difficulty_percent={"easy": 50, "medium": 50},
            custom_instruction=None,
            seed=42,
        )

        total_questions = sum(b.n_questions for b in batches)
        assert total_questions == 6

        question_types = {b.question_type for b in batches}
        assert "mcq4" in question_types
        assert "true_false" in question_types
        assert "short_answer" in question_types

    def test_difficulty_distribution(self):
        """Test that difficulty is distributed across batches."""
        batches = build_batches_end_to_end(
            question_type_counts={"mcq4": 10},
            concepts=["Concept A"],
            difficulty_percent={"easy": 50, "medium": 30, "hard": 20},
            custom_instruction=None,
            seed=42,
        )

        difficulties = {b.difficulty for b in batches}
        assert "easy" in difficulties
        assert "medium" in difficulties or "hard" in difficulties  # At least one more

    def test_custom_instruction_fraction(self):
        """Test that custom_instruction is applied to fraction of batches."""
        batches = build_batches_end_to_end(
            question_type_counts={"mcq4": 10},
            concepts=["A", "B", "C"],
            difficulty_percent={"easy": 50, "medium": 50},
            custom_instruction="Test instruction",
            custom_instruction_fraction=0.30,
            seed=42,
        )

        with_instruction = [b for b in batches if b.custom_instruction is not None]
        without_instruction = [b for b in batches if b.custom_instruction is None]

        # About 30% should have instructions
        total = len(batches)
        expected_with = round(total * 0.30)
        assert len(with_instruction) == expected_with

    def test_raises_error_for_no_question_types(self):
        """Test that error is raised when no question types have count > 0."""
        with pytest.raises(ValueError, match="No question types"):
            build_batches_end_to_end(
                question_type_counts={"mcq4": 0, "true_false": 0},
                concepts=["A"],
                difficulty_percent={"easy": 100},
                custom_instruction=None,
            )

    def test_raises_error_for_empty_concepts(self):
        """Test that error is raised for empty concepts list."""
        with pytest.raises(ValueError, match="concepts must be a non-empty"):
            build_batches_end_to_end(
                question_type_counts={"mcq4": 5},
                concepts=[],
                difficulty_percent={"easy": 100},
                custom_instruction=None,
            )

    def test_single_concept_multiple_questions(self):
        """Test with single concept and multiple questions (concept repetition)."""
        batches = build_batches_end_to_end(
            question_type_counts={"mcq4": 7},
            concepts=["Single Concept"],
            difficulty_percent={"easy": 100},
            custom_instruction=None,
            seed=42,
        )

        total_questions = sum(b.n_questions for b in batches)
        assert total_questions == 7

        # All batches should have the single concept
        for batch in batches:
            assert "Single Concept" in batch.concepts

    def test_more_concepts_than_questions(self):
        """Test when concepts outnumber questions."""
        batches = build_batches_end_to_end(
            question_type_counts={"mcq4": 2},
            concepts=[f"Concept {i}" for i in range(10)],
            difficulty_percent={"easy": 100},
            custom_instruction=None,
            seed=42,
            shuffle_input_concepts=False,
        )

        total_questions = sum(b.n_questions for b in batches)
        assert total_questions == 2

        # Should use all 10 concepts distributed across batches
        all_concepts = []
        for batch in batches:
            all_concepts.extend(batch.concepts)
        assert len(set(all_concepts)) >= 2  # At least some concepts used


# ============================================================================
# TESTS FOR HELPER FUNCTIONS IN question_generator.py
# ============================================================================


class TestExtractQuestionTypeCounts:
    """Tests for extract_question_type_counts_dict function."""

    def test_extracts_counts_correctly(self):
        """Test that question type counts are extracted correctly."""
        request = GenerateQuestionsRequest(
            activity_id=uuid.uuid4(),
            concept_ids=[uuid.uuid4()],
            config=QuestionConfig(
                question_types=[
                    QuestionTypeConfig(type="mcq4", count=5),
                    QuestionTypeConfig(type="true_false", count=3),
                    QuestionTypeConfig(
                        type="short_answer", count=0
                    ),  # Should be excluded
                ],
                difficulty_distribution=DifficultyDistribution(
                    easy=50, medium=30, hard=20
                ),
            ),
        )

        result = extract_question_type_counts_dict(request)

        assert result == {"mcq4": 5, "true_false": 3}
        assert "short_answer" not in result  # Zero count excluded


class TestExtractDifficultyPercentages:
    """Tests for extract_difficulty_percentages function."""

    def test_extracts_percentages_correctly(self):
        """Test that difficulty percentages are extracted correctly."""
        difficulty = DifficultyDistribution(easy=50, medium=30, hard=20)
        result = extract_difficulty_percentages(difficulty)

        assert result == {"easy": 50, "medium": 30, "hard": 20}


class TestGenerateQuestionsPrompt:
    """Tests for generate_questions_prompt function."""

    def test_generates_prompt_with_concepts(self):
        """Test that prompt includes concept information."""
        prompt = generate_questions_prompt(
            concepts=["Concept A", "Concept B"],
            concepts_descriptions={
                "Concept A": "Description A",
                "Concept B": "Description B",
            },
            old_questions_on_concepts=[],
            n=3,
            question_type="mcq4",
            difficulty="easy",
        )

        assert "Concept A" in prompt
        assert "Concept B" in prompt
        assert "Description A" in prompt
        assert "mcq4" in prompt
        assert "easy" in prompt
        assert "3" in prompt

    def test_generates_prompt_with_instructions(self):
        """Test that prompt includes user instructions when provided."""
        prompt = generate_questions_prompt(
            concepts=["Test Concept"],
            concepts_descriptions={"Test Concept": "Test Description"},
            old_questions_on_concepts=[],
            n=2,
            question_type="true_false",
            difficulty="medium",
            instructions="Focus on practical examples",
        )

        assert "Focus on practical examples" in prompt

    def test_generates_prompt_without_instructions(self):
        """Test that prompt works without instructions."""
        prompt = generate_questions_prompt(
            concepts=["Test Concept"],
            concepts_descriptions={"Test Concept": "Test Description"},
            old_questions_on_concepts=[],
            n=2,
            question_type="true_false",
            difficulty="medium",
            instructions=None,
        )

        assert "Test Concept" in prompt
        assert "Additional user instructions" not in prompt


# ============================================================================
# TESTS FOR generate_questions_for_batches
# ============================================================================


class TestGenerateQuestionsForBatches:
    """Tests for the generate_questions_for_batches function."""

    @pytest.fixture
    def sample_batches(self) -> List[Batch]:
        """Create sample batches for testing."""
        return [
            Batch(
                question_type="mcq4",
                difficulty="easy",
                n_questions=2,
                concepts=["Newton's Laws of Motion", "Kinetic Energy"],
                custom_instruction=None,
            ),
            Batch(
                question_type="true_false",
                difficulty="medium",
                n_questions=1,
                concepts=["Potential Energy"],
                custom_instruction="Focus on real-world examples",
            ),
        ]

    @pytest.mark.asyncio
    async def test_returns_list_of_dicts(
        self,
        gemini_client: genai.Client,
        sample_batches: List[Batch],
        mock_concepts_dict: Dict[str, str],
        mock_concepts_name_to_id: Dict[str, str],
        mock_old_questions: List[dict],
        mock_activity_id: uuid.UUID,
    ):
        """Test that generate_questions_for_batches returns a list of dicts."""
        result = await generate_questions_for_batches(
            gemini_client=gemini_client,
            batches=sample_batches,
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
            assert "concept_ids" in item

    @pytest.mark.asyncio
    async def test_question_dict_has_required_fields(
        self,
        gemini_client: genai.Client,
        sample_batches: List[Batch],
        mock_concepts_dict: Dict[str, str],
        mock_concepts_name_to_id: Dict[str, str],
        mock_old_questions: List[dict],
        mock_activity_id: uuid.UUID,
    ):
        """Test that each generated question dict has required fields."""
        result = await generate_questions_for_batches(
            gemini_client=gemini_client,
            batches=sample_batches,
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

    @pytest.mark.asyncio
    async def test_concept_ids_are_list(
        self,
        gemini_client: genai.Client,
        sample_batches: List[Batch],
        mock_concepts_dict: Dict[str, str],
        mock_concepts_name_to_id: Dict[str, str],
        mock_old_questions: List[dict],
        mock_activity_id: uuid.UUID,
    ):
        """Test that concept_ids is a list."""
        result = await generate_questions_for_batches(
            gemini_client=gemini_client,
            batches=sample_batches,
            concepts_dict=mock_concepts_dict,
            concepts_name_to_id=mock_concepts_name_to_id,
            old_questions=mock_old_questions,
            activity_id=mock_activity_id,
        )

        for item in result:
            assert isinstance(item["concept_ids"], list)
            assert len(item["concept_ids"]) >= 1

    @pytest.mark.asyncio
    async def test_hardness_level_matches_batch_difficulty(
        self,
        gemini_client: genai.Client,
        mock_concepts_dict: Dict[str, str],
        mock_concepts_name_to_id: Dict[str, str],
        mock_old_questions: List[dict],
        mock_activity_id: uuid.UUID,
    ):
        """Test that hardness_level in questions matches batch difficulty."""
        easy_batch = [
            Batch(
                question_type="mcq4",
                difficulty="easy",
                n_questions=1,
                concepts=["Newton's Laws of Motion"],
                custom_instruction=None,
            ),
        ]

        result = await generate_questions_for_batches(
            gemini_client=gemini_client,
            batches=easy_batch,
            concepts_dict=mock_concepts_dict,
            concepts_name_to_id=mock_concepts_name_to_id,
            old_questions=mock_old_questions,
            activity_id=mock_activity_id,
        )

        for item in result:
            assert (
                item["question"]["hardness_level"] == PublicHardnessLevelEnumEnum.EASY
            )

    @pytest.mark.asyncio
    async def test_handles_duplicate_concepts_in_batch(
        self,
        gemini_client: genai.Client,
        mock_concepts_dict: Dict[str, str],
        mock_concepts_name_to_id: Dict[str, str],
        mock_old_questions: List[dict],
        mock_activity_id: uuid.UUID,
    ):
        """Test that duplicate concepts in batch are deduplicated."""
        batch_with_duplicates = [
            Batch(
                question_type="mcq4",
                difficulty="easy",
                n_questions=2,
                # Duplicate concepts
                concepts=[
                    "Newton's Laws of Motion",
                    "Newton's Laws of Motion",
                    "Kinetic Energy",
                ],
                custom_instruction=None,
            ),
        ]

        result = await generate_questions_for_batches(
            gemini_client=gemini_client,
            batches=batch_with_duplicates,
            concepts_dict=mock_concepts_dict,
            concepts_name_to_id=mock_concepts_name_to_id,
            old_questions=mock_old_questions,
            activity_id=mock_activity_id,
        )

        # concept_ids should be deduplicated
        for item in result:
            concept_ids = item["concept_ids"]
            # Should have no duplicates
            assert len(concept_ids) == len(set(concept_ids))

    @pytest.mark.asyncio
    async def test_empty_batches_returns_empty_list(
        self,
        gemini_client: genai.Client,
        mock_concepts_dict: Dict[str, str],
        mock_concepts_name_to_id: Dict[str, str],
        mock_old_questions: List[dict],
        mock_activity_id: uuid.UUID,
    ):
        """Test that empty batches list returns empty result."""
        result = await generate_questions_for_batches(
            gemini_client=gemini_client,
            batches=[],
            concepts_dict=mock_concepts_dict,
            concepts_name_to_id=mock_concepts_name_to_id,
            old_questions=mock_old_questions,
            activity_id=mock_activity_id,
        )

        assert result == []

    @pytest.mark.asyncio
    async def test_custom_marks(
        self,
        gemini_client: genai.Client,
        sample_batches: List[Batch],
        mock_concepts_dict: Dict[str, str],
        mock_concepts_name_to_id: Dict[str, str],
        mock_old_questions: List[dict],
        mock_activity_id: uuid.UUID,
    ):
        """Test that custom marks value is applied."""
        custom_marks = 5

        result = await generate_questions_for_batches(
            gemini_client=gemini_client,
            batches=sample_batches,
            concepts_dict=mock_concepts_dict,
            concepts_name_to_id=mock_concepts_name_to_id,
            old_questions=mock_old_questions,
            activity_id=mock_activity_id,
            default_marks=custom_marks,
        )

        for item in result:
            assert item["question"]["marks"] == custom_marks

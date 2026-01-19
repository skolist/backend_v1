"""
Contains the logic to batchify question generation requests based on various parameters.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Any, Optional
import random
import math


# ----------------------------
# Data structure
# ----------------------------
@dataclass(frozen=True)
class Batch:
    """Batch definition."""

    question_type: str
    difficulty: str
    n_questions: int  # <= max_questions_per_batch
    concepts: List[str]  # at least 1 concept per batch
    custom_instruction: Any  # str | list | dict | None


# ----------------------------
# Helpers
# ----------------------------
def _dedupe_preserve_order(items: List[str]) -> List[str]:
    seen = set()
    out = []
    for x in items:
        xs = str(x).strip()
        if xs and xs not in seen:
            seen.add(xs)
            out.append(xs)
    return out


def _normalize_weights(weights: Dict[str, float]) -> Dict[str, float]:
    cleaned = {k: float(v) for k, v in weights.items() if float(v) >= 0.0}
    s = sum(cleaned.values())
    if s <= 0:
        raise ValueError("All weights are zero/negative; at least one must be > 0.")
    return {k: v / s for k, v in cleaned.items()}


def _largest_remainder_apportion(
    total: int,
    keys: List[str],
    weights: Dict[str, float],
) -> Dict[str, int]:
    """
    Integer apportionment using Largest Remainder method.
    Sums exactly to `total`. Zero weights naturally get 0.
    """
    if total < 0:
        raise ValueError("total must be >= 0")

    w = {k: float(weights.get(k, 0.0)) for k in keys}
    if sum(w.values()) <= 0 or total == 0:
        return {k: 0 for k in keys}

    w_norm = _normalize_weights(w)
    ideals = {k: w_norm[k] * total for k in keys}
    floors = {k: int(math.floor(ideals[k])) for k in keys}
    used = sum(floors.values())
    rem = total - used

    remainders = sorted(
        keys, key=lambda k: (ideals[k] - floors[k], w_norm[k]), reverse=True
    )
    for k in remainders[:rem]:
        floors[k] += 1

    return floors


def _chunk_questions(n: int, max_per_chunk: int = 3) -> List[int]:
    if n < 0:
        raise ValueError("n must be >= 0")
    out: List[int] = []
    while n > 0:
        take = min(max_per_chunk, n)
        out.append(take)
        n -= take
    return out


def _expand_concepts_to_slots(
    concepts: List[str],
    slots: int,
    *,
    rng: random.Random,
    shuffle_each_cycle: bool = True,
) -> List[str]:
    """
    If concepts < slots, repeat concepts until length==slots.
    Repetition happens ONLY when needed.
    """
    if slots <= 0:
        return []
    if not concepts:
        raise ValueError("concepts must be non-empty.")

    base = concepts[:]
    if len(base) >= slots:
        return base[:slots]

    expanded: List[str] = []
    while len(expanded) < slots:
        cycle = base[:]
        if shuffle_each_cycle:
            rng.shuffle(cycle)
        expanded.extend(cycle)
    return expanded[:slots]


def _apply_custom_instruction_fraction(
    batches: List[Batch],
    custom_instruction_value: Any,
    fraction: float,
    *,
    mode: str = "first",  # "first" or "random"
    seed: Optional[int] = None,
) -> List[Batch]:
    """
    Keep custom_instruction only in fraction of batches; others -> None.
    fraction rounding: k = round(N * fraction)
    """
    if not 0.0 <= fraction <= 1.0:
        raise ValueError("fraction must be between 0 and 1")

    n = len(batches)
    k = int(round(n * fraction))

    if k <= 0:
        return [
            Batch(b.question_type, b.difficulty, b.n_questions, b.concepts, None)
            for b in batches
        ]
    if k >= n:
        return [
            Batch(
                b.question_type,
                b.difficulty,
                b.n_questions,
                b.concepts,
                custom_instruction_value,
            )
            for b in batches
        ]

    idxs = list(range(n))
    if mode == "random":
        random.Random(seed).shuffle(idxs)
    elif mode != "first":
        raise ValueError("mode must be 'first' or 'random'")

    chosen = set(idxs[:k])
    updated: List[Batch] = []
    for i, b in enumerate(batches):
        ci = custom_instruction_value if i in chosen else None
        updated.append(
            Batch(b.question_type, b.difficulty, b.n_questions, b.concepts, ci)
        )
    return updated


# ----------------------------
# Main API
# ----------------------------
# pylint: disable=too-many-branches, too-many-statements
def build_batches_end_to_end(
    question_type_counts: Dict[str, int],
    concepts: List[str],
    difficulty_percent: Dict[str, float],
    custom_instruction: Any,
    *,
    max_questions_per_batch: int = 3,
    seed: Optional[int] = None,
    shuffle_input_concepts: bool = True,
    custom_instruction_fraction: float = 0.30,
    custom_instruction_mode: str = "first",  # "first" or "random"
) -> List[Batch]:
    """
    End-to-end batch builder.

    Core behavior:
    - If concepts >= total_questions:
        - use concepts uniquely (no overlap across types)
        - consume ALL concepts.
    - If concepts < total_questions:
        - repeat concepts ONLY as needed so that we have one concept-slot per question.
    - Difficulty buckets with 0% or 0 questions are removed.
    - Every produced batch has at least 1 concept.
    - Each (type,difficulty) bucket is split into granular batches of <=3 questions.
    - Custom instruction appears in only ~30% batches (rounded), rest None.
    """
    active_types = [
        (qt, int(cnt)) for qt, cnt in question_type_counts.items() if int(cnt) > 0
    ]
    if not active_types:
        raise ValueError("No question types with count > 0 provided.")

    base_concepts = _dedupe_preserve_order(concepts)
    if not base_concepts:
        raise ValueError("concepts must be a non-empty list of non-empty strings.")

    rng = random.Random(seed)
    if shuffle_input_concepts:
        rng.shuffle(base_concepts)

    total_questions = sum(cnt for _, cnt in active_types)

    # Difficulty normalization (missing difficulties = 0 implicitly)
    diff_norm = _normalize_weights(difficulty_percent)
    diff_keys = list(diff_norm.keys())

    if len(base_concepts) < total_questions:
        concept_slots = _expand_concepts_to_slots(
            base_concepts, slots=total_questions, rng=rng, shuffle_each_cycle=True
        )
    else:
        concept_slots = base_concepts[:]  # use ALL concepts

    total_slots = len(concept_slots)

    # Allocate slots across question types proportional to their question counts
    type_keys = [qt for qt, _ in active_types]
    type_weights = {qt: cnt / total_questions for qt, cnt in active_types}
    slots_per_type = _largest_remainder_apportion(total_slots, type_keys, type_weights)
    type_slots: Dict[str, List[str]] = {}
    idx = 0
    for qt in type_keys:
        n = slots_per_type[qt]
        type_slots[qt] = concept_slots[idx : idx + n]
        idx += n
    zero_types = [qt for qt in type_keys if len(type_slots[qt]) == 0]
    if zero_types:
        donors = [qt for qt in type_keys if len(type_slots[qt]) > 1]
        if len(donors) < len(zero_types):
            raise ValueError(
                "Not enough concept slots to ensure at least 1 concept per active question type. "
                "Increase concepts or reduce active types."
            )
        for zt in zero_types:
            donor = donors.pop(0)
            # move last slot from donor to zero type
            moved = type_slots[donor][-1]
            type_slots[donor] = type_slots[donor][:-1]
            type_slots[zt] = [moved]

    # Build batches per type -> difficulty -> chunks
    batches: List[Batch] = []

    for qt, q_count in active_types:
        # Questions per difficulty for this type
        q_per_diff = _largest_remainder_apportion(q_count, diff_keys, diff_norm)

        # Concept-slots for this type are distributed across difficulties,
        # proportional to question counts
        # IMPORTANT: If slots_mode=="use_all_concepts",
        # slots_per_type can exceed q_count; still fine.
        # We distribute all slots of this type across difficulties using the same diff weights.
        slots = type_slots[qt]
        s_count = len(slots)
        s_per_diff = _largest_remainder_apportion(s_count, diff_keys, diff_norm)

        s_idx = 0
        for diff in diff_keys:
            n_q = q_per_diff.get(diff, 0)
            n_s = s_per_diff.get(diff, 0)

            # remove unnecessary difficulty batches
            if diff_norm.get(diff, 0.0) <= 0.0 or n_q <= 0 or n_s <= 0:
                s_idx += n_s
                continue

            diff_slots = slots[s_idx : s_idx + n_s]
            s_idx += n_s

            # Split questions into chunks <= max_questions_per_batch
            q_chunks = _chunk_questions(n_q, max_questions_per_batch)

            # Split diff_slots across chunks proportional to chunk sizes
            chunk_keys = [str(i) for i in range(len(q_chunks))]
            chunk_weights = {str(i): q_chunks[i] / n_q for i in range(len(q_chunks))}
            s_per_chunk = _largest_remainder_apportion(
                len(diff_slots), chunk_keys, chunk_weights
            )

            pos = 0
            for i, qn in enumerate(q_chunks):
                take = s_per_chunk[str(i)]
                concepts_for_batch = diff_slots[pos : pos + take]
                pos += take

                # Guarantee at least 1 concept in every batch (your constraint).
                # If allocation gave 0, borrow from remaining if possible;
                # else borrow from previous portion.
                if not concepts_for_batch:
                    if pos < len(diff_slots):
                        concepts_for_batch = [diff_slots[pos]]
                        pos += 1
                    else:
                        # last resort: reuse one concept from this diff
                        concepts_for_batch = [diff_slots[-1]]

                batches.append(
                    Batch(
                        question_type=qt,
                        difficulty=diff,
                        n_questions=qn,
                        concepts=concepts_for_batch,
                        custom_instruction=custom_instruction,  # will be pruned to 30% later
                    )
                )

        if s_idx != len(slots):
            raise RuntimeError(f"Internal error: slot slicing mismatch for type={qt}.")

    # Apply custom-instruction fraction (30% present, rest None)
    batches = _apply_custom_instruction_fraction(
        batches,
        custom_instruction_value=custom_instruction,
        fraction=custom_instruction_fraction,
        mode=custom_instruction_mode,
        seed=seed,
    )

    # Final validations
    if sum(b.n_questions for b in batches) != total_questions:
        raise RuntimeError("Internal error: total questions mismatch.")

    if not all(b.n_questions <= max_questions_per_batch for b in batches):
        raise RuntimeError("Internal error: chunking constraint violated.")

    if not all(len(b.concepts) >= 1 for b in batches):
        raise RuntimeError("Internal error: zero-concept batch exists.")

    return batches

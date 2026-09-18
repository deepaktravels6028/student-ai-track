"""
tests/test_quiz_engine.py
-------------------------
Unit tests for quiz_engine.py.
No network calls, no file I/O.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from models import QuizQuestion
from quiz_engine import find_weak_areas, needs_revision, score_quiz


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_q(correct: str, user: str, tag: str = "topic") -> QuizQuestion:
    return QuizQuestion(
        question_text="Q?",
        options={"A": "a", "B": "b", "C": "c", "D": "d"},
        correct_answer=correct,
        topic_tag=tag,
        user_answer=user,
    )


# ── score_quiz ────────────────────────────────────────────────────────────────


class TestScoreQuiz:
    def test_all_correct(self):
        questions = [_make_q("A", "A"), _make_q("B", "B"), _make_q("C", "C")]
        assert score_quiz(questions) == 3

    def test_all_wrong(self):
        questions = [_make_q("A", "B"), _make_q("B", "C"), _make_q("C", "D")]
        assert score_quiz(questions) == 0

    def test_mixed(self):
        questions = [_make_q("A", "A"), _make_q("B", "C"), _make_q("C", "C")]
        assert score_quiz(questions) == 2

    def test_empty_list(self):
        assert score_quiz([]) == 0

    def test_single_correct(self):
        assert score_quiz([_make_q("D", "D")]) == 1

    def test_single_wrong(self):
        assert score_quiz([_make_q("D", "A")]) == 0


# ── find_weak_areas ───────────────────────────────────────────────────────────


class TestFindWeakAreas:
    def test_returns_wrong_tags(self):
        questions = [
            _make_q("A", "B", "loops"),
            _make_q("B", "B", "functions"),
        ]
        result = find_weak_areas(questions)
        assert result == ["loops"]

    def test_deduplicates_tags(self):
        questions = [
            _make_q("A", "B", "loops"),
            _make_q("A", "B", "loops"),   # same tag, wrong again
        ]
        result = find_weak_areas(questions)
        assert result == ["loops"]

    def test_all_correct_returns_empty(self):
        questions = [_make_q("A", "A", "loops"), _make_q("B", "B", "functions")]
        assert find_weak_areas(questions) == []

    def test_preserves_order_of_first_occurrence(self):
        questions = [
            _make_q("A", "B", "variables"),
            _make_q("A", "B", "loops"),
            _make_q("A", "B", "variables"),  # duplicate
        ]
        result = find_weak_areas(questions)
        assert result == ["variables", "loops"]

    def test_empty_list(self):
        assert find_weak_areas([]) == []


# ── needs_revision ────────────────────────────────────────────────────────────


class TestNeedsRevision:
    def test_below_threshold(self):
        assert needs_revision(2, 5) is True   # 40 % < 60 %

    def test_at_threshold(self):
        # exactly 60 % is NOT below threshold
        assert needs_revision(3, 5) is False

    def test_above_threshold(self):
        assert needs_revision(4, 5) is False

    def test_zero_total_returns_false(self):
        assert needs_revision(0, 0) is False

    def test_perfect_score(self):
        assert needs_revision(5, 5) is False

    def test_zero_score(self):
        assert needs_revision(0, 5) is True

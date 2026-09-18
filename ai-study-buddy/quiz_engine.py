"""
quiz_engine.py
--------------
Pure business logic for quiz scoring and weak-area detection.
No UI, no API calls — only plain Python functions.
"""

from __future__ import annotations

from models import QuizQuestion

# ── Constants ────────────────────────────────────────────────────────────────

PASS_THRESHOLD: float = 0.6   # 60 % correct → revision plan is skipped


def score_quiz(questions: list[QuizQuestion]) -> int:
    """
    Count the number of correctly answered questions.

    Parameters
    ----------
    questions: List of QuizQuestion objects with user_answer filled in.

    Returns
    -------
    Integer count of correct answers (0 – len(questions)).
    """
    return sum(
        1 for q in questions if q.user_answer == q.correct_answer
    )


def find_weak_areas(questions: list[QuizQuestion]) -> list[str]:
    """
    Return the unique topic tags for every incorrectly answered question.

    Parameters
    ----------
    questions: List of QuizQuestion objects with user_answer filled in.

    Returns
    -------
    Deduplicated list of topic_tag strings (order preserved by first occurrence).
    """
    seen: set[str] = set()
    weak: list[str] = []
    for q in questions:
        if q.user_answer != q.correct_answer and q.topic_tag not in seen:
            seen.add(q.topic_tag)
            weak.append(q.topic_tag)
    return weak


def needs_revision(score: int, total: int) -> bool:
    """
    Return True if the student's score is below the pass threshold.

    Parameters
    ----------
    score: Number of correct answers.
    total: Total number of questions.
    """
    if total == 0:
        return False
    return (score / total) < PASS_THRESHOLD

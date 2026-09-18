"""
models.py
---------
Pure data classes — no business logic, no I/O.
All other modules import from here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class QuizQuestion:
    """A single multiple-choice question generated from study notes."""

    question_text: str
    options: dict[str, str]          # {"A": "...", "B": "...", "C": "...", "D": "..."}
    correct_answer: str              # One of "A", "B", "C", "D"
    topic_tag: str                   # Short label for the concept being tested
    user_answer: str = ""            # Filled in by the user during the quiz

    def to_dict(self) -> dict[str, Any]:
        return {
            "question_text": self.question_text,
            "options": self.options,
            "correct_answer": self.correct_answer,
            "topic_tag": self.topic_tag,
            "user_answer": self.user_answer,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "QuizQuestion":
        return cls(
            question_text=data["question_text"],
            options=data["options"],
            correct_answer=data["correct_answer"],
            topic_tag=data["topic_tag"],
            user_answer=data.get("user_answer", ""),
        )


@dataclass
class RevisionPlan:
    """A simple revision plan generated from the student's weak areas."""

    weak_topics: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    generated_text: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "weak_topics": self.weak_topics,
            "suggestions": self.suggestions,
            "generated_text": self.generated_text,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RevisionPlan":
        return cls(
            weak_topics=data.get("weak_topics", []),
            suggestions=data.get("suggestions", []),
            generated_text=data.get("generated_text", ""),
        )


@dataclass
class StudySession:
    """Everything recorded for a single study session."""

    session_id: str
    timestamp: str
    subject: str
    raw_notes: str
    eli10_explanation: str = ""
    quiz_questions: list[QuizQuestion] = field(default_factory=list)
    score: int = 0
    weak_areas: list[str] = field(default_factory=list)
    revision_plan: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "timestamp": self.timestamp,
            "subject": self.subject,
            "raw_notes": self.raw_notes,
            "eli10_explanation": self.eli10_explanation,
            "quiz_questions": [q.to_dict() for q in self.quiz_questions],
            "score": self.score,
            "weak_areas": self.weak_areas,
            "revision_plan": self.revision_plan,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "StudySession":
        return cls(
            session_id=data["session_id"],
            timestamp=data["timestamp"],
            subject=data["subject"],
            raw_notes=data["raw_notes"],
            eli10_explanation=data.get("eli10_explanation", ""),
            quiz_questions=[
                QuizQuestion.from_dict(q) for q in data.get("quiz_questions", [])
            ],
            score=data.get("score", 0),
            weak_areas=data.get("weak_areas", []),
            revision_plan=data.get("revision_plan", ""),
        )

"""
tests/test_validators.py
------------------------
Unit tests for validators.py.
No network calls, no file I/O.
"""

from __future__ import annotations

import io
import sys
from pathlib import Path

import pytest

# Make the project root importable from the tests/ subdirectory
sys.path.insert(0, str(Path(__file__).parent.parent))

from exceptions import (
    EmptyNotesError,
    InvalidFileTypeError,
    NoSubjectSelectedError,
    NotesTooLongError,
    NotesTooShortError,
)
from validators import (
    SUBJECT_PLACEHOLDER,
    validate_file,
    validate_notes,
    validate_quiz_answers,
    validate_subject,
)
from models import QuizQuestion


# ── validate_notes ────────────────────────────────────────────────────────────


class TestValidateNotes:
    def test_valid_notes_returns_cleaned_text(self):
        notes = "  " + "A" * 60 + "  "
        result = validate_notes(notes)
        assert result == "A" * 60

    def test_strips_html_tags(self):
        notes = "<p>" + "B" * 60 + "</p>"
        result = validate_notes(notes)
        assert "<p>" not in result
        assert len(result) >= 50

    def test_empty_string_raises(self):
        with pytest.raises(EmptyNotesError):
            validate_notes("")

    def test_whitespace_only_raises(self):
        with pytest.raises(EmptyNotesError):
            validate_notes("   \n\t  ")

    def test_html_only_raises_empty(self):
        # After stripping tags nothing remains
        with pytest.raises(EmptyNotesError):
            validate_notes("<p><br/></p>")

    def test_too_short_raises(self):
        with pytest.raises(NotesTooShortError):
            validate_notes("Too short")

    def test_exactly_min_length_passes(self):
        notes = "x" * 50
        assert validate_notes(notes) == notes

    def test_too_long_raises(self):
        with pytest.raises(NotesTooLongError):
            validate_notes("x" * 5_001)

    def test_exactly_max_length_passes(self):
        notes = "x" * 5_000
        assert validate_notes(notes) == notes


# ── validate_subject ─────────────────────────────────────────────────────────


class TestValidateSubject:
    def test_valid_subject_returns_unchanged(self):
        assert validate_subject("Math") == "Math"

    def test_placeholder_raises(self):
        with pytest.raises(NoSubjectSelectedError):
            validate_subject(SUBJECT_PLACEHOLDER)

    def test_empty_string_raises(self):
        with pytest.raises(NoSubjectSelectedError):
            validate_subject("")


# ── validate_file ─────────────────────────────────────────────────────────────


class _FakeFile:
    """Minimal stand-in for a Streamlit UploadedFile."""

    def __init__(self, name: str, content: bytes):
        self.name = name
        self._content = content

    def read(self) -> bytes:
        return self._content


class TestValidateFile:
    def test_valid_txt_file_returns_content(self):
        content = b"Hello world " * 10
        fake = _FakeFile("notes.txt", content)
        result = validate_file(fake)
        assert result == content.decode("utf-8")

    def test_non_txt_raises(self):
        fake = _FakeFile("notes.pdf", b"PDF data")
        with pytest.raises(InvalidFileTypeError):
            validate_file(fake)

    def test_binary_content_raises(self):
        fake = _FakeFile("notes.txt", bytes(range(256)))
        with pytest.raises(InvalidFileTypeError):
            validate_file(fake)

    def test_uppercase_extension_passes(self):
        content = b"Hello world " * 10
        fake = _FakeFile("notes.TXT", content)
        result = validate_file(fake)
        assert result == content.decode("utf-8")


# ── validate_quiz_answers ────────────────────────────────────────────────────


def _make_question(user_answer: str = "") -> QuizQuestion:
    return QuizQuestion(
        question_text="What is 2+2?",
        options={"A": "3", "B": "4", "C": "5", "D": "6"},
        correct_answer="B",
        topic_tag="arithmetic",
        user_answer=user_answer,
    )


class TestValidateQuizAnswers:
    def test_all_answered_passes(self):
        questions = [_make_question("A"), _make_question("B"), _make_question("C")]
        validate_quiz_answers(questions)  # should not raise

    def test_missing_answer_raises(self):
        questions = [_make_question("A"), _make_question(""), _make_question("C")]
        with pytest.raises(ValueError, match="Q2"):
            validate_quiz_answers(questions)

    def test_all_empty_raises(self):
        questions = [_make_question(), _make_question(), _make_question()]
        with pytest.raises(ValueError):
            validate_quiz_answers(questions)

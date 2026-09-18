"""
validators.py
-------------
All input validation logic for AI Study Buddy.
Each function raises a specific custom exception on failure
and returns the clean/normalised value on success.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from exceptions import (
    EmptyNotesError,
    InvalidFileTypeError,
    NoSubjectSelectedError,
    NotesTooLongError,
    NotesTooShortError,
)

if TYPE_CHECKING:
    from models import QuizQuestion

# ── Constants ────────────────────────────────────────────────────────────────

MIN_NOTES_LENGTH: int = 50
MAX_NOTES_LENGTH: int = 5_000
SUBJECT_PLACEHOLDER: str = "-- Select a subject --"
VALID_SUBJECTS: tuple[str, ...] = ("Python", "Math", "Science", "History", "Other")

# ── Tag stripper ─────────────────────────────────────────────────────────────

_HTML_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(text: str) -> str:
    """Remove HTML tags from a string."""
    return _HTML_TAG_RE.sub("", text)


# ── Public validators ────────────────────────────────────────────────────────

def validate_notes(text: str) -> str:
    """
    Validate and normalise study notes.

    Steps:
    1. Strip surrounding whitespace.
    2. Strip HTML tags (handles copy-paste from web pages).
    3. Enforce minimum and maximum length.

    Returns the cleaned notes string.
    Raises EmptyNotesError, NotesTooShortError, or NotesTooLongError.
    """
    cleaned = _strip_html(text).strip()

    if not cleaned:
        raise EmptyNotesError("Please enter or upload your study notes.")

    if len(cleaned) < MIN_NOTES_LENGTH:
        raise NotesTooShortError(
            f"Notes are too short ({len(cleaned)} characters). "
            f"Please add at least {MIN_NOTES_LENGTH} characters."
        )

    if len(cleaned) > MAX_NOTES_LENGTH:
        raise NotesTooLongError(
            f"Notes exceed the {MAX_NOTES_LENGTH:,} character limit "
            f"({len(cleaned):,} characters). Please shorten them."
        )

    return cleaned


def validate_subject(subject: str) -> str:
    """
    Validate the selected subject category.

    Returns the subject string unchanged.
    Raises NoSubjectSelectedError if the placeholder or an empty value is given.
    """
    if not subject or subject == SUBJECT_PLACEHOLDER:
        raise NoSubjectSelectedError("Please select a subject category.")

    return subject


def validate_file(uploaded_file: object) -> str:
    """
    Validate an uploaded file object (Streamlit UploadedFile).

    Checks:
    - Extension must be .txt
    - Content must be decodable as UTF-8 text

    Returns the file content as a string.
    Raises InvalidFileTypeError on any failure.
    """
    name: str = getattr(uploaded_file, "name", "")
    if not name.lower().endswith(".txt"):
        raise InvalidFileTypeError(
            f"Only .txt files are supported. You uploaded: '{name}'"
        )

    try:
        raw_bytes: bytes = uploaded_file.read()
        content = raw_bytes.decode("utf-8")
    except (UnicodeDecodeError, AttributeError) as exc:
        raise InvalidFileTypeError(
            "Could not read the file. Please ensure it is plain text (UTF-8)."
        ) from exc

    return content


def validate_quiz_answers(questions: list["QuizQuestion"]) -> None:
    """
    Ensure every quiz question has been answered before scoring.

    Raises ValueError with a user-friendly message if any answer is missing.
    """
    unanswered = [
        i + 1 for i, q in enumerate(questions) if not q.user_answer
    ]
    if unanswered:
        nums = ", ".join(str(n) for n in unanswered)
        raise ValueError(
            f"Please answer all questions before submitting. "
            f"Unanswered: Q{nums}."
        )

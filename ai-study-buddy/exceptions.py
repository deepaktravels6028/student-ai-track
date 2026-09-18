"""
exceptions.py
-------------
Custom exception hierarchy for AI Study Buddy.
All exceptions are caught at the UI layer (app.py) and rendered
as st.error() messages — never expose raw tracebacks to the user.
"""


class StudyBuddyError(Exception):
    """Base class for all AI Study Buddy errors."""


# ── Input / Validation errors ────────────────────────────────────────────────

class EmptyNotesError(StudyBuddyError):
    """Raised when the user submits blank or whitespace-only notes."""


class NotesTooShortError(StudyBuddyError):
    """Raised when notes are below the minimum length (50 characters)."""


class NotesTooLongError(StudyBuddyError):
    """Raised when notes exceed the maximum length (5 000 characters)."""


class NoSubjectSelectedError(StudyBuddyError):
    """Raised when the user has not chosen a subject category."""


class InvalidFileTypeError(StudyBuddyError):
    """Raised when the uploaded file is not a plain-text (.txt) file."""


# ── AI / API errors ──────────────────────────────────────────────────────────

class AIResponseParseError(StudyBuddyError):
    """Raised when the LLM response cannot be parsed into a quiz structure."""


class AIServiceError(StudyBuddyError):
    """Raised when the LLM API call fails (network error, timeout, auth, etc.)."""


# ── Persistence errors ───────────────────────────────────────────────────────

class SessionSaveError(StudyBuddyError):
    """Raised when writing a session to sessions.json fails."""


class SessionLoadError(StudyBuddyError):
    """Raised when sessions.json cannot be read or is corrupted."""

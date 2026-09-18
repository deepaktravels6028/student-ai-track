"""
session_manager.py
------------------
Handles reading and writing of study sessions to a local JSON file.
The rest of the app never touches file I/O directly.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from exceptions import SessionLoadError, SessionSaveError
from models import StudySession

# ── Config ────────────────────────────────────────────────────────────────────

SESSIONS_FILE: Path = Path(os.getenv("SESSIONS_FILE", "sessions.json"))


# ── Public functions ──────────────────────────────────────────────────────────


def save_session(session: StudySession) -> None:
    """
    Append a completed study session to the JSON file.

    - Creates sessions.json if it does not yet exist.
    - Raises SessionSaveError on any IO failure.
    """
    existing = _load_raw()   # list[dict]
    existing.append(session.to_dict())
    try:
        SESSIONS_FILE.write_text(
            json.dumps(existing, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    except OSError as exc:
        raise SessionSaveError(
            f"Could not save the session: {exc}"
        ) from exc


def load_all_sessions() -> list[StudySession]:
    """
    Load and return all past study sessions.

    - Returns an empty list on the first run (file not yet created).
    - Raises SessionLoadError if the file exists but cannot be parsed.
    """
    raw = _load_raw()
    try:
        return [StudySession.from_dict(d) for d in raw]
    except (KeyError, TypeError, ValueError) as exc:
        raise SessionLoadError(
            f"sessions.json is corrupted and could not be loaded: {exc}"
        ) from exc


def get_session_by_id(session_id: str) -> StudySession | None:
    """
    Return the session matching session_id, or None if not found.
    """
    for session in load_all_sessions():
        if session.session_id == session_id:
            return session
    return None


# ── Internal helpers ──────────────────────────────────────────────────────────


def _load_raw() -> list[dict]:
    """
    Read sessions.json and return its contents as a list of dicts.
    Returns an empty list if the file does not exist.
    Raises SessionLoadError if JSON parsing fails.
    """
    if not SESSIONS_FILE.exists():
        return []
    try:
        text = SESSIONS_FILE.read_text(encoding="utf-8")
        data = json.loads(text)
        if not isinstance(data, list):
            raise SessionLoadError("sessions.json must contain a JSON array.")
        return data
    except json.JSONDecodeError as exc:
        raise SessionLoadError(
            f"sessions.json contains invalid JSON: {exc}"
        ) from exc

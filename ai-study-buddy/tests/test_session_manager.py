"""
tests/test_session_manager.py
-----------------------------
Unit tests for session_manager.py.
File I/O is redirected to a temp directory so real sessions.json is never touched.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

import session_manager
from exceptions import SessionLoadError, SessionSaveError
from models import QuizQuestion, StudySession


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _tmp_sessions_file(tmp_path, monkeypatch):
    """Redirect SESSIONS_FILE to a temp path for every test."""
    fake_path = tmp_path / "sessions.json"
    monkeypatch.setattr(session_manager, "SESSIONS_FILE", fake_path)
    return fake_path


def _make_session(session_id: str = "s1", score: int = 3) -> StudySession:
    q = QuizQuestion(
        question_text="What is Python?",
        options={"A": "Snake", "B": "Language", "C": "Tool", "D": "IDE"},
        correct_answer="B",
        topic_tag="basics",
        user_answer="B",
    )
    return StudySession(
        session_id=session_id,
        timestamp="2024-01-01 10:00",
        subject="Python",
        raw_notes="Python is a programming language." * 5,
        eli10_explanation="Python is like giving instructions to a robot.",
        quiz_questions=[q],
        score=score,
        weak_areas=[],
        revision_plan="",
    )


# ── save_session ──────────────────────────────────────────────────────────────


class TestSaveSession:
    def test_creates_file_on_first_save(self, tmp_path):
        sess = _make_session()
        session_manager.save_session(sess)
        assert session_manager.SESSIONS_FILE.exists()

    def test_saved_content_is_valid_json(self):
        sess = _make_session()
        session_manager.save_session(sess)
        data = json.loads(session_manager.SESSIONS_FILE.read_text())
        assert isinstance(data, list)
        assert len(data) == 1

    def test_multiple_saves_appended(self):
        session_manager.save_session(_make_session("s1"))
        session_manager.save_session(_make_session("s2"))
        data = json.loads(session_manager.SESSIONS_FILE.read_text())
        assert len(data) == 2

    def test_save_error_on_read_only_path(self, monkeypatch):
        monkeypatch.setattr(
            session_manager, "SESSIONS_FILE", Path("/nonexistent_dir/sessions.json")
        )
        with pytest.raises(SessionSaveError):
            session_manager.save_session(_make_session())


# ── load_all_sessions ────────────────────────────────────────────────────────


class TestLoadAllSessions:
    def test_returns_empty_list_when_no_file(self):
        result = session_manager.load_all_sessions()
        assert result == []

    def test_round_trip(self):
        original = _make_session("abc", score=4)
        session_manager.save_session(original)
        loaded = session_manager.load_all_sessions()
        assert len(loaded) == 1
        assert loaded[0].session_id == "abc"
        assert loaded[0].score == 4

    def test_corrupted_json_raises(self):
        session_manager.SESSIONS_FILE.write_text("NOT JSON", encoding="utf-8")
        with pytest.raises(SessionLoadError):
            session_manager.load_all_sessions()

    def test_non_array_json_raises(self):
        session_manager.SESSIONS_FILE.write_text('{"key": "value"}', encoding="utf-8")
        with pytest.raises(SessionLoadError):
            session_manager.load_all_sessions()


# ── get_session_by_id ────────────────────────────────────────────────────────


class TestGetSessionById:
    def test_returns_matching_session(self):
        session_manager.save_session(_make_session("find_me"))
        result = session_manager.get_session_by_id("find_me")
        assert result is not None
        assert result.session_id == "find_me"

    def test_returns_none_when_not_found(self):
        session_manager.save_session(_make_session("exists"))
        result = session_manager.get_session_by_id("does_not_exist")
        assert result is None

    def test_returns_none_on_empty_file(self):
        result = session_manager.get_session_by_id("any_id")
        assert result is None

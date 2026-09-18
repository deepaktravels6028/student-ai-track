"""
tests/test_ai_helper.py
-----------------------
Unit tests for ai_helper.py.
All Anthropic API calls are mocked — no real network calls are made.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from exceptions import AIResponseParseError, AIServiceError
from models import QuizQuestion
import ai_helper


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_mock_response(text: str) -> MagicMock:
    """Build a minimal mock that looks like an Anthropic Message."""
    content_block = MagicMock()
    content_block.text = text
    msg = MagicMock()
    msg.content = [content_block]
    return msg


VALID_QUIZ_TEXT = """\
QUESTION: What is a variable in Python?
A: A type of loop
B: A storage location for data
C: A function definition
D: An import statement
CORRECT: B
TAG: variables
---
QUESTION: Which keyword defines a function?
A: class
B: var
C: def
D: func
CORRECT: C
TAG: functions
---
QUESTION: What does print() do?
A: Reads input
B: Imports a module
C: Defines a class
D: Outputs text to the console
CORRECT: D
TAG: output
---
"""


# ── parse_quiz_response ───────────────────────────────────────────────────────


class TestParseQuizResponse:
    def test_parses_valid_quiz(self):
        questions = ai_helper.parse_quiz_response(VALID_QUIZ_TEXT)
        assert len(questions) == 3
        assert all(isinstance(q, QuizQuestion) for q in questions)

    def test_correct_answers_extracted(self):
        questions = ai_helper.parse_quiz_response(VALID_QUIZ_TEXT)
        assert questions[0].correct_answer == "B"
        assert questions[1].correct_answer == "C"
        assert questions[2].correct_answer == "D"

    def test_options_dict_has_four_keys(self):
        questions = ai_helper.parse_quiz_response(VALID_QUIZ_TEXT)
        for q in questions:
            assert set(q.options.keys()) == {"A", "B", "C", "D"}

    def test_topic_tags_extracted(self):
        questions = ai_helper.parse_quiz_response(VALID_QUIZ_TEXT)
        assert questions[0].topic_tag == "variables"
        assert questions[1].topic_tag == "functions"

    def test_user_answer_starts_empty(self):
        questions = ai_helper.parse_quiz_response(VALID_QUIZ_TEXT)
        for q in questions:
            assert q.user_answer == ""

    def test_malformed_block_skipped(self):
        bad_text = "NOT A VALID BLOCK\n---\n" + VALID_QUIZ_TEXT
        questions = ai_helper.parse_quiz_response(bad_text)
        assert len(questions) == 3  # bad block skipped, 3 valid ones remain

    def test_too_few_questions_raises(self):
        # Only 1 valid block — below MIN_VALID_QUESTIONS (3)
        single = """\
QUESTION: Only question?
A: Yes
B: No
C: Maybe
D: Always
CORRECT: A
TAG: misc
---
"""
        with pytest.raises(AIResponseParseError):
            ai_helper.parse_quiz_response(single)

    def test_invalid_correct_letter_skipped(self):
        bad_correct = """\
QUESTION: Bad correct?
A: Yes
B: No
C: Maybe
D: Always
CORRECT: Z
TAG: misc
---
"""
        # 1 invalid + 3 valid = only 3 parsed
        result = ai_helper.parse_quiz_response(bad_correct + VALID_QUIZ_TEXT)
        assert len(result) == 3


# ── generate_eli10 ────────────────────────────────────────────────────────────


class TestGenerateEli10:
    @patch("ai_helper._call_api")
    def test_returns_explanation_string(self, mock_call):
        mock_call.return_value = "Python is like giving instructions to a robot."
        result = ai_helper.generate_eli10("Python is a language.", "Python")
        assert isinstance(result, str)
        assert len(result) > 0
        mock_call.assert_called_once()

    @patch("ai_helper._call_api")
    def test_subject_included_in_prompt(self, mock_call):
        mock_call.return_value = "explanation"
        ai_helper.generate_eli10("some notes " * 10, "History")
        prompt_used = mock_call.call_args[0][0]
        assert "History" in prompt_used

    @patch("ai_helper._call_api", side_effect=AIServiceError("API down"))
    def test_propagates_ai_service_error(self, _mock_call):
        with pytest.raises(AIServiceError):
            ai_helper.generate_eli10("notes " * 10, "Math")


# ── generate_quiz ─────────────────────────────────────────────────────────────


class TestGenerateQuiz:
    @patch("ai_helper._call_api")
    def test_returns_list_of_quiz_questions(self, mock_call):
        mock_call.return_value = VALID_QUIZ_TEXT
        result = ai_helper.generate_quiz("Python notes " * 10, "Python")
        assert isinstance(result, list)
        assert len(result) == 3
        assert all(isinstance(q, QuizQuestion) for q in result)

    @patch("ai_helper._call_api")
    def test_raises_parse_error_on_bad_response(self, mock_call):
        mock_call.return_value = "This is not a quiz format at all."
        with pytest.raises(AIResponseParseError):
            ai_helper.generate_quiz("notes " * 10, "Science")

    @patch("ai_helper._call_api", side_effect=AIServiceError("timeout"))
    def test_propagates_ai_service_error(self, _mock_call):
        with pytest.raises(AIServiceError):
            ai_helper.generate_quiz("notes " * 10, "Math")


# ── generate_revision_plan ────────────────────────────────────────────────────


class TestGenerateRevisionPlan:
    @patch("ai_helper._call_api")
    def test_returns_string(self, mock_call):
        mock_call.return_value = "• Review loops\n• Practice functions"
        result = ai_helper.generate_revision_plan(
            ["loops", "functions"], "Python", "notes " * 10
        )
        assert isinstance(result, str)
        assert len(result) > 0

    @patch("ai_helper._call_api")
    def test_weak_areas_in_prompt(self, mock_call):
        mock_call.return_value = "plan text"
        ai_helper.generate_revision_plan(["variables", "loops"], "Python", "notes " * 10)
        prompt_used = mock_call.call_args[0][0]
        assert "variables" in prompt_used
        assert "loops" in prompt_used

    @patch("ai_helper._call_api")
    def test_empty_weak_areas_uses_general_review(self, mock_call):
        mock_call.return_value = "general plan"
        ai_helper.generate_revision_plan([], "Math", "notes " * 10)
        prompt_used = mock_call.call_args[0][0]
        assert "general review" in prompt_used


# ── _call_api error handling ──────────────────────────────────────────────────


class TestCallApiErrors:
    @patch("ai_helper._get_client")
    def test_authentication_error_wrapped(self, mock_get_client):
        import anthropic
        mock_get_client.return_value.messages.create.side_effect = (
            anthropic.AuthenticationError.__new__(anthropic.AuthenticationError)
        )
        with pytest.raises(AIServiceError, match="Invalid Anthropic API key"):
            ai_helper._call_api("test prompt")

    @patch("ai_helper._get_client")
    def test_connection_error_wrapped(self, mock_get_client):
        import anthropic
        mock_get_client.return_value.messages.create.side_effect = (
            anthropic.APIConnectionError.__new__(anthropic.APIConnectionError)
        )
        with pytest.raises(AIServiceError, match="Could not reach"):
            ai_helper._call_api("test prompt")

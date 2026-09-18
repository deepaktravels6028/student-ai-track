"""
ai_helper.py
------------
All interactions with the Anthropic Claude API.
Business logic (scoring, session management) lives elsewhere.
"""

from __future__ import annotations

import os
import re
from typing import Any

import anthropic
from dotenv import load_dotenv

from exceptions import AIResponseParseError, AIServiceError
from models import QuizQuestion

load_dotenv()

# ── Constants ────────────────────────────────────────────────────────────────

MODEL: str = "claude-3-haiku-20240307"   # Fast, cheap, free-tier friendly
MAX_TOKENS: int = 1_024
MIN_VALID_QUESTIONS: int = 3             # Accept partial quiz if ≥ 3 parsed OK

# ── Delimiter used in quiz prompts ───────────────────────────────────────────

QUIZ_DELIMITER: str = "---"

# ── Internal helper ──────────────────────────────────────────────────────────


def _get_client() -> anthropic.Anthropic:
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise AIServiceError(
            "ANTHROPIC_API_KEY is not set. "
            "Add it to your .env file and restart the app."
        )
    return anthropic.Anthropic(api_key=api_key)


def _call_api(prompt: str) -> str:
    """
    Send a single user message to Claude and return the text response.
    Wraps all Anthropic SDK errors into AIServiceError.
    """
    try:
        client = _get_client()
        message = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text
    except AIServiceError:
        raise
    except anthropic.AuthenticationError as exc:
        raise AIServiceError(
            "Invalid Anthropic API key. Check your .env file."
        ) from exc
    except anthropic.RateLimitError as exc:
        raise AIServiceError(
            "Anthropic rate limit reached. Please wait a moment and try again."
        ) from exc
    except anthropic.APIConnectionError as exc:
        raise AIServiceError(
            "Could not reach the Anthropic API. Check your internet connection."
        ) from exc
    except anthropic.APIStatusError as exc:
        raise AIServiceError(
            f"Anthropic API error ({exc.status_code}): {exc.message}"
        ) from exc
    except Exception as exc:
        raise AIServiceError(f"Unexpected error calling the AI service: {exc}") from exc


# ── Public API functions ──────────────────────────────────────────────────────


def generate_eli10(notes: str, subject: str) -> str:
    """
    Return a child-friendly (ELI10) explanation of the study notes.

    Parameters
    ----------
    notes:   Validated study notes text.
    subject: Subject category (e.g. "Python", "Math").

    Returns
    -------
    A plain-text explanation suitable for a 10-year-old.
    """
    prompt = (
        f"You are a friendly teacher explaining {subject} to a 10-year-old child.\n"
        f"Read the following study notes and explain the key ideas in very simple, "
        f"everyday language. Use short sentences, simple words, and a fun analogy "
        f"if it helps. Do NOT use technical jargon.\n\n"
        f"STUDY NOTES:\n{notes}\n\n"
        f"Write your simple explanation below:"
    )
    return _call_api(prompt)


def generate_quiz(notes: str, subject: str) -> list[QuizQuestion]:
    """
    Generate 3–5 multiple-choice questions from the study notes.

    Returns a list of QuizQuestion objects.
    Raises AIResponseParseError if fewer than MIN_VALID_QUESTIONS are parsed.
    """
    prompt = (
        f"You are a teacher creating a short quiz on {subject}.\n"
        f"Read the study notes below and create exactly 5 multiple-choice questions "
        f"that test understanding of the key concepts.\n\n"
        f"Rules:\n"
        f"- Each question must have exactly 4 options labelled A, B, C, D.\n"
        f"- Exactly one option must be correct.\n"
        f"- Include a short topic tag (2–4 words) describing the concept tested.\n"
        f"- Use the EXACT format shown below for every question, with '---' as separator.\n\n"
        f"FORMAT (repeat for each question):\n"
        f"QUESTION: <question text>\n"
        f"A: <option text>\n"
        f"B: <option text>\n"
        f"C: <option text>\n"
        f"D: <option text>\n"
        f"CORRECT: <A|B|C|D>\n"
        f"TAG: <short topic label>\n"
        f"---\n\n"
        f"STUDY NOTES:\n{notes}\n\n"
        f"Output the quiz questions now:"
    )
    raw_response = _call_api(prompt)
    return parse_quiz_response(raw_response)


def generate_revision_plan(weak_areas: list[str], subject: str, notes: str) -> str:
    """
    Generate a short, focused revision plan for the student's weak topics.

    Parameters
    ----------
    weak_areas: List of topic_tag strings the student answered incorrectly.
    subject:    Subject category.
    notes:      Original notes, for additional context.

    Returns
    -------
    A plain-text revision plan with bullet points.
    """
    topics_str = ", ".join(weak_areas) if weak_areas else "general review"
    prompt = (
        f"You are a helpful tutor. A student just completed a {subject} quiz "
        f"and struggled with the following topics: {topics_str}.\n\n"
        f"Based on their study notes below, write a short, encouraging revision plan "
        f"with 3–5 bullet points. Each point should name the weak topic and give "
        f"one concrete tip on how to study it better. Keep language simple and positive.\n\n"
        f"STUDY NOTES:\n{notes}\n\n"
        f"Write the revision plan below:"
    )
    return _call_api(prompt)


# ── Quiz response parser ──────────────────────────────────────────────────────


def parse_quiz_response(raw_text: str) -> list[QuizQuestion]:
    """
    Convert the raw LLM quiz text into a list of QuizQuestion objects.

    Expected block format (separated by '---'):
        QUESTION: ...
        A: ...
        B: ...
        C: ...
        D: ...
        CORRECT: A|B|C|D
        TAG: ...

    Malformed blocks are skipped silently.
    Raises AIResponseParseError if fewer than MIN_VALID_QUESTIONS are parsed.
    """
    questions: list[QuizQuestion] = []
    blocks = raw_text.split(QUIZ_DELIMITER)

    for block in blocks:
        block = block.strip()
        if not block:
            continue

        parsed = _parse_single_block(block)
        if parsed is not None:
            questions.append(parsed)

    if len(questions) < MIN_VALID_QUESTIONS:
        raise AIResponseParseError(
            f"The AI returned only {len(questions)} valid question(s); "
            f"expected at least {MIN_VALID_QUESTIONS}. Please try again."
        )

    return questions


def _parse_single_block(block: str) -> QuizQuestion | None:
    """
    Parse one question block. Returns None if the block is malformed.
    """
    def _extract(label: str, text: str) -> str:
        match = re.search(
            rf"^{re.escape(label)}:\s*(.+)$", text, re.MULTILINE | re.IGNORECASE
        )
        return match.group(1).strip() if match else ""

    question_text = _extract("QUESTION", block)
    option_a = _extract("A", block)
    option_b = _extract("B", block)
    option_c = _extract("C", block)
    option_d = _extract("D", block)
    correct = _extract("CORRECT", block).upper()
    tag = _extract("TAG", block)

    # All fields must be present and correct must be a valid option letter
    if not all([question_text, option_a, option_b, option_c, option_d, tag]):
        return None
    if correct not in ("A", "B", "C", "D"):
        return None

    return QuizQuestion(
        question_text=question_text,
        options={"A": option_a, "B": option_b, "C": option_c, "D": option_d},
        correct_answer=correct,
        topic_tag=tag,
    )

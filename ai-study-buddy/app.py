"""
app.py
------
Streamlit entry point for AI Study Buddy.
All UI code lives here; business logic is imported from other modules.
"""

from __future__ import annotations

import uuid
from datetime import datetime

import streamlit as st

import ai_helper
import quiz_engine
import session_manager
from exceptions import (
    AIResponseParseError,
    AIServiceError,
    EmptyNotesError,
    InvalidFileTypeError,
    NoSubjectSelectedError,
    NotesTooLongError,
    NotesTooShortError,
    SessionLoadError,
    SessionSaveError,
    StudyBuddyError,
)
from models import StudySession
from validators import (
    SUBJECT_PLACEHOLDER,
    VALID_SUBJECTS,
    validate_file,
    validate_notes,
    validate_quiz_answers,
    validate_subject,
)

# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="AI Study Buddy",
    page_icon="📚",
    layout="centered",
)

# ── Session-state initialisation ──────────────────────────────────────────────
# All keys must exist before any widget references them to avoid KeyError.

_STATE_DEFAULTS: dict = {
    "notes": "",
    "subject": "",
    "eli10": "",
    "questions": [],
    "score": 0,
    "weak_areas": [],
    "revision_plan": "",
    "session_saved": False,
    "quiz_submitted": False,
    "session_started": False,
}

for _key, _val in _STATE_DEFAULTS.items():
    if _key not in st.session_state:
        st.session_state[_key] = _val


# ── Helper ────────────────────────────────────────────────────────────────────


def _reset_session() -> None:
    """Clear all session-state keys back to their defaults."""
    for key, val in _STATE_DEFAULTS.items():
        st.session_state[key] = val


# ── Header ────────────────────────────────────────────────────────────────────

st.title("📚 AI Study Buddy")
st.caption("Paste your notes, get a simple explanation, take a quiz, and review your weak areas.")

st.divider()

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — Notes Input
# ═══════════════════════════════════════════════════════════════════════════════

st.header("1️⃣  Your Study Notes")

subject = st.selectbox(
    "Subject / Topic Category",
    options=[SUBJECT_PLACEHOLDER, *VALID_SUBJECTS],
    index=0,
)

uploaded_file = st.file_uploader("Upload a .txt file (optional)", type=["txt"])

notes_input = st.text_area(
    "Or paste your notes here",
    height=200,
    placeholder="Paste your study notes, a chapter summary, or a syllabus topic…",
)

# Character counter
char_count = len(notes_input)
st.caption(f"{char_count:,} / 5,000 characters")

if not st.session_state["session_started"]:
    if st.button("▶️  Start Session", type="primary"):
        try:
            # File upload overwrites the text area
            if uploaded_file is not None:
                raw_text = validate_file(uploaded_file)
            else:
                raw_text = notes_input

            clean_notes = validate_notes(raw_text)
            clean_subject = validate_subject(subject)

            st.session_state["notes"] = clean_notes
            st.session_state["subject"] = clean_subject
            st.session_state["session_started"] = True
            st.rerun()

        except (EmptyNotesError, NotesTooShortError, NotesTooLongError) as exc:
            st.error(f"📝 {exc}")
        except NoSubjectSelectedError as exc:
            st.error(f"📂 {exc}")
        except InvalidFileTypeError as exc:
            st.error(f"📄 {exc}")
else:
    st.success(
        f"✅ Session started — **{st.session_state['subject']}**  "
        f"({len(st.session_state['notes']):,} characters)"
    )
    if st.button("🔄  Start New Session"):
        _reset_session()
        st.rerun()

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — ELI10 Explanation
# ═══════════════════════════════════════════════════════════════════════════════

if st.session_state["session_started"]:
    st.divider()
    st.header("2️⃣  Explain It Simply (ELI10)")

    if not st.session_state["eli10"]:
        if st.button("💡  Explain Like I'm 10"):
            with st.spinner("Asking the AI to simplify your notes…"):
                try:
                    explanation = ai_helper.generate_eli10(
                        st.session_state["notes"],
                        st.session_state["subject"],
                    )
                    st.session_state["eli10"] = explanation
                    st.rerun()
                except AIServiceError as exc:
                    st.error(f"🤖 AI Error: {exc}")
    else:
        st.info(st.session_state["eli10"])

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 3 — Quiz
# ═══════════════════════════════════════════════════════════════════════════════

if st.session_state["session_started"]:
    st.divider()
    st.header("3️⃣  Quiz Time")

    if not st.session_state["questions"]:
        if st.button("📝  Generate Quiz Questions"):
            with st.spinner("Creating quiz questions from your notes…"):
                try:
                    questions = ai_helper.generate_quiz(
                        st.session_state["notes"],
                        st.session_state["subject"],
                    )
                    st.session_state["questions"] = questions
                    st.rerun()
                except (AIServiceError, AIResponseParseError) as exc:
                    st.error(f"🤖 AI Error: {exc}")

    elif not st.session_state["quiz_submitted"]:
        st.write(f"Answer all **{len(st.session_state['questions'])}** questions, then click **Submit**.")

        for idx, question in enumerate(st.session_state["questions"]):
            st.markdown(f"**Q{idx + 1}: {question.question_text}**")
            options_list = [
                f"{letter}: {text}"
                for letter, text in question.options.items()
            ]
            choice = st.radio(
                label=f"Q{idx + 1}",
                options=options_list,
                index=None,
                key=f"q_{idx}",
                label_visibility="collapsed",
            )
            # Extract just the letter (e.g. "A") from "A: some text"
            if choice is not None:
                st.session_state["questions"][idx].user_answer = choice[0]
            st.write("")  # spacer

        if st.button("✅  Submit Answers", type="primary"):
            try:
                validate_quiz_answers(st.session_state["questions"])

                score = quiz_engine.score_quiz(st.session_state["questions"])
                weak_areas = quiz_engine.find_weak_areas(st.session_state["questions"])

                st.session_state["score"] = score
                st.session_state["weak_areas"] = weak_areas
                st.session_state["quiz_submitted"] = True
                st.rerun()

            except ValueError as exc:
                st.warning(f"⚠️ {exc}")

    else:
        # Quiz locked — show which answers were right/wrong
        st.write("**Your answers:**")
        for idx, question in enumerate(st.session_state["questions"]):
            is_correct = question.user_answer == question.correct_answer
            icon = "✅" if is_correct else "❌"
            st.markdown(
                f"{icon} **Q{idx + 1}:** {question.question_text}  \n"
                f"Your answer: **{question.user_answer}** — "
                f"Correct: **{question.correct_answer}**"
            )

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 4 — Score & Revision Plan
# ═══════════════════════════════════════════════════════════════════════════════

if st.session_state["quiz_submitted"]:
    st.divider()
    st.header("4️⃣  Score & Revision Plan")

    total = len(st.session_state["questions"])
    score = st.session_state["score"]
    pct = int(score / total * 100) if total else 0

    st.metric(label="Your Score", value=f"{score} / {total}", delta=f"{pct}%")

    if score == total:
        st.success("🎉 Perfect score! Excellent work — no revision needed.")
    elif quiz_engine.needs_revision(score, total):
        st.warning(f"📖 You scored below 60%. Let's build a revision plan for your weak areas.")

        if not st.session_state["revision_plan"]:
            if st.button("📋  Generate Revision Plan"):
                with st.spinner("Building your personalised revision plan…"):
                    try:
                        plan = ai_helper.generate_revision_plan(
                            st.session_state["weak_areas"],
                            st.session_state["subject"],
                            st.session_state["notes"],
                        )
                        st.session_state["revision_plan"] = plan
                        st.rerun()
                    except AIServiceError as exc:
                        st.error(f"🤖 AI Error: {exc}")
        else:
            st.subheader("Your Revision Plan")
            st.warning(st.session_state["revision_plan"])
    else:
        st.success(f"👍 Good job! You passed. Score: {pct}%")

    # ── Save session ──────────────────────────────────────────────────────────
    if not st.session_state["session_saved"]:
        try:
            new_session = StudySession(
                session_id=str(uuid.uuid4()),
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M"),
                subject=st.session_state["subject"],
                raw_notes=st.session_state["notes"],
                eli10_explanation=st.session_state["eli10"],
                quiz_questions=st.session_state["questions"],
                score=st.session_state["score"],
                weak_areas=st.session_state["weak_areas"],
                revision_plan=st.session_state["revision_plan"],
            )
            session_manager.save_session(new_session)
            st.session_state["session_saved"] = True
        except SessionSaveError as exc:
            st.error(f"💾 Could not save session: {exc}")

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 5 — Session History
# ═══════════════════════════════════════════════════════════════════════════════

st.divider()
st.header("5️⃣  Past Study Sessions")

try:
    past_sessions = session_manager.load_all_sessions()
except SessionLoadError as exc:
    st.error(f"📂 Could not load history: {exc}")
    past_sessions = []

if not past_sessions:
    st.caption("No sessions saved yet. Complete a quiz to save your first session!")
else:
    # Show most recent first
    for sess in reversed(past_sessions):
        label = (
            f"📅 {sess.timestamp}  |  📂 {sess.subject}  |  "
            f"⭐ Score: {sess.score}/{len(sess.quiz_questions)}"
        )
        with st.expander(label):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**Subject:** {sess.subject}")
                st.markdown(f"**Date:** {sess.timestamp}")
                st.markdown(f"**Score:** {sess.score} / {len(sess.quiz_questions)}")
            with col2:
                if sess.weak_areas:
                    st.markdown(f"**Weak areas:** {', '.join(sess.weak_areas)}")
                else:
                    st.markdown("**Weak areas:** None 🎉")

            if sess.eli10_explanation:
                st.markdown("**Simple Explanation:**")
                st.info(sess.eli10_explanation[:500] + ("…" if len(sess.eli10_explanation) > 500 else ""))

            if sess.revision_plan:
                st.markdown("**Revision Plan:**")
                st.warning(sess.revision_plan[:500] + ("…" if len(sess.revision_plan) > 500 else ""))

            st.markdown("**Notes snippet:**")
            st.caption(sess.raw_notes[:300] + ("…" if len(sess.raw_notes) > 300 else ""))

# AI Study Buddy — Project Plan

## Top-Level Overview

Build a beginner-friendly, single-page Streamlit application called **AI Study Buddy**.  
The app lets a student paste or upload study notes, pick a subject, and then:
- Get a plain-English "Explain Like I'm 10" (ELI10) summary from Google Gemini
- Take a 5-question multiple-choice quiz generated from their notes
- See their score and identify weak areas
- Read an AI-generated revision plan targeting those weak spots
- Browse a history of all past sessions stored in a local `sessions.json` file

**Constraints:**
- Python + Streamlit only (no database, no login, no backend server)
- Google Gemini Free Tier for all AI calls
- Single scrollable page layout
- One-shot quiz flow — no retakes; start fresh for a new session
- Beginner-friendly code: small files, clear naming, minimal abstractions

---

## Project File Structure

```
ai-study-buddy/
├── app.py                  # Streamlit entry point — all UI code
├── ai_helper.py            # All Google Gemini API calls + response parsing
├── quiz_engine.py          # Quiz scoring and weak-area detection
├── session_manager.py      # Save/load sessions.json
├── models.py               # Data classes: StudySession, QuizQuestion, RevisionPlan
├── validators.py           # Input validation functions
├── exceptions.py           # Custom exception classes
├── sessions.json           # Auto-created on first save (gitignore this)
├── requirements.txt        # google-generativeai, streamlit
└── .env                    # GEMINI_API_KEY (gitignore this)
```

---

## Sub-Tasks

---

### Sub-Task 1 — Data Models

**Intent**  
Define the plain Python data classes that all other modules will import and use.  
Getting this right first prevents circular imports and keeps the data contract clear.

**Expected Outcomes**
- `models.py` contains `QuizQuestion`, `RevisionPlan`, and `StudySession` dataclasses
- All fields match the spec below
- No logic — pure data containers only

**Data Fields**

`QuizQuestion`
| Field | Type | Notes |
|---|---|---|
| question_text | str | The question string |
| options | dict[str, str] | Keys: "A", "B", "C", "D" |
| correct_answer | str | One of "A", "B", "C", "D" |
| user_answer | str | Empty string until answered |
| topic_tag | str | Short label for the concept tested |

`RevisionPlan`
| Field | Type | Notes |
|---|---|---|
| weak_topics | list[str] | topic_tag values where user was wrong |
| suggestions | list[str] | One tip per weak topic |
| generated_text | str | Full AI-written revision summary |

`StudySession`
| Field | Type | Notes |
|---|---|---|
| session_id | str | Timestamp-based unique ID |
| timestamp | str | Human-readable datetime string |
| subject | str | Selected category |
| raw_notes | str | Original pasted/uploaded text |
| eli10_explanation | str | AI simplified explanation |
| quiz_questions | list[QuizQuestion] | The 5 generated questions |
| score | int | Number correct out of 5 |
| weak_areas | list[str] | topic_tag values from wrong answers |
| revision_plan | str | AI revision summary text |

**Todo List**
- [ ] Create `models.py` with three dataclasses using `@dataclass` decorator
- [ ] Use `field(default_factory=list)` for list fields
- [ ] Add a `to_dict()` and `from_dict()` method to `StudySession` for JSON serialisation
- [ ] Add a `to_dict()` and `from_dict()` method to `QuizQuestion` for JSON serialisation

**Relevant Context**
- `session_manager.py` will call `to_dict()` when saving and `from_dict()` when loading
- All other modules import from `models.py` — no other cross-imports

**Status:** [ ] pending

---

### Sub-Task 2 — Custom Exceptions

**Intent**  
Define all custom exception classes in one place so they can be raised deep in business logic and caught cleanly at the UI layer.

**Expected Outcomes**
- `exceptions.py` contains all eight exception classes
- Each class inherits from `Exception` and accepts a message string

**Exception Classes**
| Class | Raised When |
|---|---|
| EmptyNotesError | Notes are blank or whitespace-only |
| NotesTooShortError | Notes are under 50 characters |
| NotesTooLongError | Notes exceed 5000 characters |
| NoSubjectSelectedError | User has not selected a category |
| AIResponseParseError | Gemini output cannot be parsed into quiz format |
| SessionSaveError | Writing to sessions.json fails |
| SessionLoadError | sessions.json is missing or corrupted |
| InvalidFileTypeError | Uploaded file is not a .txt file |

**Todo List**
- [ ] Create `exceptions.py`
- [ ] Define all eight exception classes, each with a docstring explaining when it is raised

**Relevant Context**
- `app.py` catches all of these and renders them as `st.error()` messages
- Never expose a raw Python traceback to the user

**Status:** [ ] pending

---

### Sub-Task 3 — Input Validators

**Intent**  
Centralise all input validation so `app.py` stays clean and validation logic is testable in isolation.

**Expected Outcomes**
- `validators.py` contains one function per validation concern
- Each function raises the appropriate custom exception on failure
- Each function returns the cleaned/normalised value on success

**Validation Rules**
| Function | Rule | Exception Raised |
|---|---|---|
| validate_notes(text) | Not empty; min 50 chars; max 5000 chars; strips HTML tags | EmptyNotesError / NotesTooShortError / NotesTooLongError |
| validate_subject(subject) | Must not be the default placeholder value | NoSubjectSelectedError |
| validate_file(uploaded_file) | Extension must be .txt; content must be readable as UTF-8 | InvalidFileTypeError |
| validate_quiz_answers(questions) | All 5 questions must have a non-empty user_answer | ValueError with message |

**Todo List**
- [ ] Create `validators.py`
- [ ] Import custom exceptions from `exceptions.py`
- [ ] Implement `validate_notes` — strip HTML using `re.sub` before length check
- [ ] Implement `validate_subject` — compare against a sentinel value like `"-- Select --"`
- [ ] Implement `validate_file` — check `.name.endswith(".txt")` then decode bytes
- [ ] Implement `validate_quiz_answers` — iterate questions and check `user_answer != ""`

**Relevant Context**
- `app.py` calls these functions before triggering any AI call
- `validate_notes` is called both for pasted text and for file-upload content

**Status:** [ ] pending

---

### Sub-Task 4 — AI Helper

**Intent**  
Wrap all Google Gemini API calls in clean, single-purpose functions. Keep prompt engineering here so the rest of the app never touches raw API objects.

**Expected Outcomes**
- `ai_helper.py` contains four functions
- The Gemini API key is loaded from a `.env` file using `python-dotenv`
- Prompts always include the subject category for contextual accuracy
- Quiz output is parsed into a list of `QuizQuestion` objects

**Functions**

`generate_eli10(notes: str, subject: str) -> str`
- Prompt instructs Gemini to explain the notes as if talking to a 10-year-old
- Returns the explanation as a plain string

`generate_quiz(notes: str, subject: str) -> list[QuizQuestion]`
- Prompt instructs Gemini to return exactly 5 multiple-choice questions
- Each question must have options A/B/C/D, one correct answer, and a topic tag
- Prompt specifies a strict plain-text format for reliable parsing
- Calls `parse_quiz_response()` internally
- Raises `AIResponseParseError` if fewer than 3 valid questions are parsed

`generate_revision_plan(weak_areas: list[str], subject: str) -> str`
- Prompt instructs Gemini to give a short, focused study plan for the weak topics
- Returns the plan as a plain string

`parse_quiz_response(raw_text: str) -> list[QuizQuestion]`
- Private helper that splits raw Gemini text into `QuizQuestion` objects
- Uses a consistent delimiter format agreed in the prompt (e.g. `QUESTION:`, `A:`, `CORRECT:`, `TAG:`)
- Skips malformed questions silently; raises `AIResponseParseError` if result is too short

**Gemini Prompt Format Contract (for quiz)**
```
QUESTION: <question text>
A: <option text>
B: <option text>
C: <option text>
D: <option text>
CORRECT: <A|B|C|D>
TAG: <short topic label>
---
```

**Todo List**
- [ ] Add `google-generativeai` and `python-dotenv` to `requirements.txt`
- [ ] Create `ai_helper.py`
- [ ] Load API key from `.env` at module level using `dotenv`
- [ ] Implement `generate_eli10` with a clear, child-friendly prompt
- [ ] Implement `generate_quiz` with the strict format prompt above
- [ ] Implement `parse_quiz_response` using string splitting on the `---` delimiter
- [ ] Implement `generate_revision_plan` with a bullet-point revision prompt
- [ ] Wrap all API calls in try/except to catch network/API errors and re-raise as friendly messages

**Relevant Context**
- Gemini Free Tier model name: `gemini-1.5-flash` (fast and free)
- `QuizQuestion` is imported from `models.py`
- `AIResponseParseError` is imported from `exceptions.py`

**Status:** [ ] pending

---

### Sub-Task 5 — Quiz Engine

**Intent**  
Pure logic for scoring the quiz and identifying which topics the student is weak on — no UI, no AI calls.

**Expected Outcomes**
- `quiz_engine.py` contains two functions
- Score is an integer 0–5
- Weak areas are a list of `topic_tag` strings from incorrectly answered questions

**Functions**

`score_quiz(questions: list[QuizQuestion]) -> int`
- Counts questions where `user_answer == correct_answer`
- Returns the count

`find_weak_areas(questions: list[QuizQuestion]) -> list[str]`
- Returns the `topic_tag` of each question where `user_answer != correct_answer`
- Deduplicates the list (a tag may appear in multiple questions)

**Business Rule:** Score below 3 out of 5 (< 60%) means a revision plan is generated.

**Todo List**
- [ ] Create `quiz_engine.py`
- [ ] Implement `score_quiz`
- [ ] Implement `find_weak_areas` using a list comprehension + `list(set(...))`

**Relevant Context**
- Called from `app.py` after the user submits quiz answers
- `topic_tag` values come from `QuizQuestion.topic_tag` set by `parse_quiz_response`

**Status:** [ ] pending

---

### Sub-Task 6 — Session Manager

**Intent**  
Handle all reading and writing of `sessions.json` so the rest of the app never touches file I/O directly.

**Expected Outcomes**
- `session_manager.py` contains three functions
- `sessions.json` is created automatically if it does not exist
- Each session is stored as a JSON object; the file is a JSON array

**Functions**

`save_session(session: StudySession) -> None`
- Loads existing sessions (empty list if file missing)
- Appends the new session as a dict using `session.to_dict()`
- Writes the full array back to `sessions.json`
- Raises `SessionSaveError` on any IO exception

`load_all_sessions() -> list[StudySession]`
- Reads `sessions.json`
- Returns an empty list if the file does not exist (first run)
- Deserialises each entry using `StudySession.from_dict()`
- Raises `SessionLoadError` if JSON is malformed

`get_session_by_id(session_id: str) -> StudySession | None`
- Loads all sessions and returns the one matching `session_id`
- Returns `None` if not found

**Todo List**
- [ ] Create `session_manager.py`
- [ ] Implement `save_session` with file-not-found handling
- [ ] Implement `load_all_sessions` with empty-list fallback on missing file
- [ ] Implement `get_session_by_id`
- [ ] Add `sessions.json` to `.gitignore`

**Relevant Context**
- `StudySession.to_dict()` and `from_dict()` are defined in Sub-Task 1
- Called from `app.py` after quiz submission and when rendering history

**Status:** [ ] pending

---

### Sub-Task 7 — Streamlit UI

**Intent**  
Wire all modules together into a single-page Streamlit app. This is the only file the user interacts with. All exceptions are caught here and shown as `st.error()` messages.

**Expected Outcomes**
- `app.py` renders a clean single-page layout with clearly labelled sections
- Each section is only visible when the previous step is complete
- Session state is used to carry data between button clicks without reruns losing context
- A history section at the bottom shows all past sessions in expanders

**Page Sections and Flow**

```
[Section 1] Notes Input
  - st.selectbox for subject (Python / Math / Science / History / Other)
  - st.text_area for pasting notes
  - st.file_uploader for .txt upload (overwrites text_area content)
  - Character counter shown below text_area
  - "Start Session" button → validates inputs → saves notes + subject to session state

[Section 2] ELI10 Explanation
  - Shown after "Start Session"
  - "Explain It To Me" button → calls generate_eli10 → displays result in st.info box

[Section 3] Quiz
  - "Generate Quiz" button → calls generate_quiz → stores questions in session state
  - Renders 5 st.radio widgets, one per question
  - "Submit Answers" button → validates all answered → scores → saves session → locks UI

[Section 4] Score and Revision Plan
  - Shows score as "X / 5"
  - If score < 3: calls generate_revision_plan → displays in st.warning box
  - If score == 5: shows st.success congratulations message
  - "Start New Session" button → clears session state → reruns app

[Section 5] History
  - Always visible at bottom of page
  - Calls load_all_sessions on each page load
  - Each session shown in an st.expander labelled with timestamp + subject + score
  - Inside expander: notes snippet, ELI10, score, weak areas, revision plan
```

**Session State Keys**
| Key | Holds |
|---|---|
| `notes` | Validated notes text |
| `subject` | Selected subject string |
| `eli10` | ELI10 explanation string |
| `questions` | List of QuizQuestion objects |
| `score` | Integer score after submission |
| `weak_areas` | List of weak topic strings |
| `revision_plan` | Revision plan string |
| `session_saved` | Boolean — True after session is saved |
| `quiz_submitted` | Boolean — locks quiz UI after submission |

**Todo List**
- [ ] Create `app.py` with `st.set_page_config` at the top
- [ ] Implement Section 1 — notes input with subject selector, text area, file uploader, character counter
- [ ] Implement Section 2 — ELI10 button and result display, guarded by session state
- [ ] Implement Section 3 — quiz generation, radio widgets, submit button with full-answer validation
- [ ] Implement Section 4 — score display, conditional revision plan, new session button
- [ ] Implement Section 5 — history loader and expanders
- [ ] Wrap every AI call and session save in try/except to render st.error on failure
- [ ] Use `st.spinner` during all AI calls for UX feedback

**Relevant Context**
- All logic functions are imported from their respective modules
- All custom exceptions are imported from `exceptions.py`
- `st.session_state` must be initialised with default values at the top of the script to avoid KeyError on first load

**Status:** [ ] pending

---

### Sub-Task 8 — Requirements and Environment Setup

**Intent**  
Provide everything a beginner needs to install and run the project from scratch.

**Expected Outcomes**
- `requirements.txt` lists all dependencies with no version conflicts
- `.env.example` shows what the API key variable should look like
- `README.md` gives step-by-step run instructions

**Dependencies**
```
streamlit
google-generativeai
python-dotenv
```

**Todo List**
- [ ] Create `requirements.txt` with the three dependencies above
- [ ] Create `.env.example` with `GEMINI_API_KEY=your_key_here`
- [ ] Create `.gitignore` with `.env` and `sessions.json`
- [ ] Create `README.md` with: project description, setup steps, how to get a Gemini API key, how to run with `streamlit run app.py`

**Relevant Context**
- Gemini API key obtained free from https://aistudio.google.com/
- No `pip install` of local packages needed — all standard PyPI packages

**Status:** [ ] pending

---

## Edge Cases Addressed in This Plan

| Edge Case | Where Handled |
|---|---|
| Empty or whitespace-only notes | `validators.validate_notes` → `EmptyNotesError` |
| Notes under 50 chars | `validators.validate_notes` → `NotesTooShortError` |
| Notes over 5000 chars | `validators.validate_notes` → `NotesTooLongError` |
| No subject selected | `validators.validate_subject` → `NoSubjectSelectedError` |
| Non-.txt file uploaded | `validators.validate_file` → `InvalidFileTypeError` |
| Empty .txt file uploaded | `validate_file` then `validate_notes` both run |
| HTML tags in pasted notes | Stripped by `re.sub` inside `validate_notes` |
| Gemini returns fewer than 3 questions | `parse_quiz_response` raises `AIResponseParseError` |
| Malformed single question in response | Skipped silently; rest of quiz still usable |
| AI/network unavailable | try/except in `ai_helper.py` + `st.error` in `app.py` |
| User answers only some questions | `validate_quiz_answers` blocks submit |
| Perfect score of 5/5 | Revision plan skipped; `st.success` shown instead |
| No past sessions yet | `load_all_sessions` returns empty list; friendly message shown |
| sessions.json corrupted | `SessionLoadError` raised → `st.error` shown |
| Page rerun mid-session | `st.session_state` preserves all in-progress data |

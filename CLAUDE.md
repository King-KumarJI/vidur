# VIDUR — Claude Code Project Memory

VIDUR = Virtual Intelligent Development Understanding & Reasoning, an AI-powered Intelligent Software Project Watchdog. Full governing rules: `docs/constitution/VIDUR_CONSTITUTION.md` — read it before any development work. It outranks default behavior.

## Non-negotiable rules (from the Constitution)

- Python is the primary language (Article 40). No placeholders, TODOs, mocks, or pseudocode — every file must be production-ready (Article 30).
- Sequence: Project → Module → Submodule → File → Verification → Completion → Tracker Update → Next File (Article 25). Don't skip ahead or leave a module half-built.
- Reuse existing code before writing new code (Articles 31-32) — check `backend/app/` for an existing utility/service/repository before creating one.
- Every DB/vector operation must go through `backend/app/core/project_isolation/` — never touch Mongo/Chroma clients directly outside `backend/app/db/` (Article 21).
- Major-Project (advanced) features must ship disabled behind `backend/app/config/feature_flags.py` (Articles 41-44).
- When editing an existing file, regenerate the complete file (Article 36-37).
- After every file: run `python -m py_compile <file>` at minimum, plus any relevant unit test. Never mark something complete without passing verification (Article 50-51).
- Update `docs/tracker/development-tracker.md` after every module, using the format already in that file.
- If something needed isn't in the approved structure below and isn't explicitly requested, stop and ask instead of inventing it (Article 38).

## Project layout

- `backend/app/config/` — settings, feature flags, logging — **done**
- `backend/app/core/project_isolation/` — project context, validation, isolated resource naming — **done**
- `backend/app/middleware/` — FastAPI middleware — **done**
- `backend/app/db/mongodb/`, `backend/app/db/chromadb/` — DB clients — **done**
- `backend/app/core/{inspection_engine,ai_reasoning,nlp,ml_prediction,deep_learning_vision}/` — not yet built
- `backend/app/{services,repositories,models,schemas,memory,analytics,iot}/` — not yet built
- `backend/app/api/v1/routes/` — not yet built
- `frontend/` — dashboard UI, not yet started

## Build & verify

```
cd backend
py -3.11 -m venv venv
venv\Scripts\activate.bat
pip install -r requirements.txt
python -m py_compile app\path\to\file.py
```

Use Python 3.11, not the machine default — numpy/chromadb don't have prebuilt wheels for newer Pythons on this setup.

## Module build order

Core Config → Project Isolation → DB Layer → Inspection Engine → AI Reasoning → NLP → ML Prediction → Deep Learning Vision → Memory → API Layer.

Live status is in `docs/tracker/development-tracker.md` — read it first every session to know exactly where to resume.

## Working style

State which module/submodule/file you're on before writing code. Finish one file completely before starting the next. Follow the Response Protocol in Article 47 of the Constitution for every development response.

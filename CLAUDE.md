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

## Frontend stack & rules

- React + Vite + TypeScript + Tailwind CSS. No CSS-in-JS, no component library beyond what Tailwind covers unless explicitly approved.
- Charts: Recharts (for Article 18 analytics — Project Health Score, Inspection History, Technical Debt, Module Complexity, Bug Trends, API Reliability, Test Coverage).
- API client: a single typed client module in `frontend/src/services/` wrapping `fetch`, built from the FastAPI OpenAPI schema at the backend's `/openapi.json`. Every request must attach the `X-Project-Id` header (see `DEFAULT_PROJECT_ID_HEADER` in `backend/app/config/settings.py`) from one central place — never hard-code the header string per call site.
- State: React state/hooks + context for the active project selection. No Redux/Zustand unless the app genuinely outgrows context.
- Pages needed, one per backend engine surfaced through the API Layer: Dashboard/health overview, Project switcher, Inspection Reports, AI Reasoning insights, NLP findings, ML Prediction risk, Deep Learning Vision regressions (must handle its Major-flag-off 403 gracefully, not crash), Memory/history, Feature Flags/settings.
- Same completion rules as the backend: no placeholder components, no `TODO`, every page wired to the real API client (not mock data), verified before moving to the next file.

## Specs Module (Personal / Computer / Calendar / Environmental Metrics + Prediction)

Flags: `MAJOR_IOT_ENVIRONMENTAL_ANALYTICS` gates all raw telemetry (personal, computer, calendar, environmental). `MAJOR_PREDICTIVE_DASHBOARDS` gates the ML prediction section. No new flags.

### Metrics scope (fixed -- no additions beyond this list)
- Personal: last coding session duration, sleep/rest hours (manual input), caffeine intake (manual input, optional), typing speed (aggregate rate only, never key content), mouse activity (aggregate rate only, never continuous coordinate logging), break frequency (derived from activity gaps).
- Computer: CPU usage, RAM usage, Disk I/O, internet latency -- via `psutil` in the local agent.
- Calendar: time of day, day of week (computed, real-time), upcoming deadlines (manual entry only in VIDUR).
- Environmental: temperature, humidity, ambient light, noise level -- via ESP32/Arduino, with simulation fallback.

### Data collection architecture
A standalone local agent (`backend/scripts/local_agent.py`, run separately by the user, not part of the FastAPI server) collects computer metrics via `psutil`, personal activity rates via aggregate-only input tracking, and environmental readings, then POSTs everything to the Specs ingestion API on an interval with the active `X-Project-Id` header. VIDUR's backend never talks to hardware directly -- only the local agent touches serial ports or OS input hooks.

### Environmental: simulation with automatic hardware handoff
No hardware exists yet -- simulate by default. Each cycle, the local agent scans serial ports (`pyserial`'s `list_ports`) for a known Arduino/ESP32 USB vendor:product ID (CH340 1A86:7523, CP210x 10C4:EA60, Arduino Uno 2341:0043 -- extend as needed). Match found -> read real data, report `source: "hardware"`. No match -> generate simulated data, report `source: "simulation"`. Zero code changes needed when hardware is plugged in; the check runs every cycle.
Per-sensor presence detection requires the board's firmware to report a manifest on connect (board type + sensors present) via a documented line-based protocol (`docs/specs/serial-protocol.md`). Writing that firmware is out of scope for this Python codebase (Article 40) -- a separate task for when hardware exists.

### Missing-sensor handling (all metric categories, not just environmental)
Any missing metric is explicitly marked missing (`status: "missing"`), never fabricated, never silently defaulted. The prediction engine must degrade gracefully -- build its feature vector from whatever metrics ARE present, excluding missing ones, never blocking.

### ML Prediction Engine -- four required outputs
Trains periodically on accumulated history pulled from the Memory module; predicts live using the last-hour window as input features. Cold-start (little history) is expected -- report confidence honestly, never fabricate it.
1. Upcoming session prediction: likelihood score AND predicted outcome (duration/productivity) if one starts now.
2. Last session summary: duration + its computed Success Score.
3. Last-5-session comparison: average Success Score (0-100 per session, derived from duration vs. historical average, break frequency, activity consistency) across the 5 most recent sessions.
4. Weekly zero-fill: any Mon-Sun aggregation always emits exactly 7 points. No session that day = explicit 0, never omitted or interpolated.

### Frontend Specs page
Current-reading tiles (live-polled; `status: "missing"` shows an inline message, not a blank/fake value). Manual inputs: sleep hours, caffeine, deadlines. Real-time clock + day-of-week + deadlines list. Prediction widget with all four outputs above.

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

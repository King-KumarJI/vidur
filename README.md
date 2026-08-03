# VIDUR

**Virtual Intelligent Development Understanding & Reasoning**

VIDUR is an AI-powered Intelligent Software Project Watchdog: a FastAPI backend + React dashboard that observes, understands, remembers, validates, inspects, analyzes, predicts, and reports on the health of a software project. It is explicitly **not** a code generator, autonomous developer, or automatic bug fixer — it inspects, explains, and recommends; the developer stays the final authority over every change. VIDUR also watches its own developer's working conditions (coding sessions, machine load, environment) through its **Specs** module.

Every design and process decision in this repository is governed by:

- [`docs/constitution/VIDUR_CONSTITUTION.md`](docs/constitution/VIDUR_CONSTITUTION.md) — the project's supreme constitution (identity, mission, non-negotiable engineering laws)
- [`CLAUDE.md`](CLAUDE.md) — the working project memory/spec that translates the constitution into concrete build rules
- [`docs/tracker/development-tracker.md`](docs/tracker/development-tracker.md) — the live, module-by-module development log and the authoritative source for "what's actually done"

---

## 1. Architecture overview

```
vidur/
├── backend/          FastAPI application (Python 3.11)
├── frontend/          React + Vite + TypeScript dashboard
├── firmware/          PlatformIO firmware for the Specs environmental sensors
├── infra/docker/       Docker Compose for MongoDB + ChromaDB
├── docs/             Constitution, tracker, serial protocol spec
└── start_vidur.bat / stop_vidur.bat   One-shot local launcher/stopper (Windows)
```

### Backend (`backend/app/`)

- **`core/`** — the analysis engines, each independently gated by a feature flag:
  - `inspection_engine/` — static project inspection (the baseline pipeline every other engine builds on)
  - `ai_reasoning/` — correlates findings, assesses dependency impact, forms debugging hypotheses, and (new) turns that structured output into recommendations via a **real local LLM through Ollama**, with an automatic fallback to the original rule-based `RecommendationEngine` if Ollama is unreachable or returns something unparseable
  - `nlp/` — AST-based code-intent extraction, Chroma-embedding semantic comparison, and (new) genuine linguistic analysis via **spaCy** (`en_core_web_sm`) as a fallback pass that rescues paraphrased requirement/implementation matches the exact-keyword check would otherwise flag
  - `ml_prediction/` — risk/regression/technical-debt predictors; the Quality Trend Predictor now trains a real **scikit-learn `LinearRegression`** on historical health-score/finding-count data instead of a hand-rolled formula
  - `deep_learning_vision/` — visual regression detection between UI screenshots; primary path is real **OpenCLIP (ViT-B-32-quickgelu)** embedding + cosine similarity, with an automatic fallback to classical OpenCV + SSIM + perceptual hashing if the DL stack isn't available
  - `specs/` — the Personal/Computer/Calendar/Environmental telemetry module (storage, session derivation, Success Score, and the four-output prediction engine)
  - `project_isolation/` — per-project context, validation, isolated Mongo/Chroma resource naming
  - `feature_flags/` — currently an empty placeholder package (the real flag registry lives in `app/config/feature_flags.py`, see §4)
- **`api/v1/`** — versioned FastAPI routers, one per engine, mounted under `/api/v1` (plus a top-level `/health`)
- **`services/`, `repositories/`, `models/`, `schemas/`** — the orchestration/persistence/contract layers between routes and `core/` engines
- **`memory/`** — the project's persistent inspection/finding history (Mongo-backed), feeding trend charts and ML training data
- **`db/mongodb/`, `db/chromadb/`** — the only code allowed to touch Mongo/Chroma clients directly; everything else goes through `core/project_isolation/`
- **`middleware/`** — `ProjectIsolationMiddleware`, enforcing the `X-Project-Id` header on every project-scoped route
- **`config/`** — `settings.py` (env-driven `Settings`) and `feature_flags.py` (the real flag registry)
- **`analytics/`, `iot/`** — present in the tree but currently empty placeholder packages; analytics is served today via `memory`'s trend endpoints and the frontend's Recharts widgets, and IoT device logic lives in `firmware/` + `backend/scripts/local_agent.py` rather than here

### Frontend (`frontend/`)

React 19 + Vite 8 + TypeScript + Tailwind CSS v4, no CSS-in-JS, no component library beyond Tailwind, Recharts for charts, React Router for navigation, React state/context (`ProjectContext`) for the active-project selection — no Redux/Zustand. A single typed client (`src/services/apiClient.ts`) wraps `fetch` and attaches `X-Project-Id` from one central place (`src/services/projectId.ts`) on every request.

### Specs data path

`backend/scripts/local_agent.py` is a **standalone script**, run separately by the user (never imported by the FastAPI server). It collects computer metrics via `psutil`, aggregate-only keyboard/mouse activity rates via `pynput`, and environmental readings — real, over serial, from an ESP32/Arduino if one is plugged in (auto-detected by USB VID:PID, then confirmed with an `IDENTIFY` handshake), otherwise simulated — and POSTs everything to the Specs ingestion API on an interval, tagged with the active `X-Project-Id`. The FastAPI backend never talks to hardware directly.

### Firmware (`firmware/`)

One shared PlatformIO codebase (`firmware/src/main.cpp`) implementing [`docs/specs/serial-protocol.md`](docs/specs/serial-protocol.md) for a DHT22 (temperature/humidity), a BH1750 (ambient light), and an analog sound sensor, compiled across four board environments (see §8). **Compile-verified only — not yet verified against physical hardware.**

---

## 2. Prerequisites

| Tool | Version | Why |
|---|---|---|
| **Python** | **3.11** (exactly — not the machine's default) | `numpy`/`chromadb`/`torch` in `requirements.txt` don't have prebuilt wheels for newer CPython versions on this setup |
| **Node.js** | 22 LTS or newer | Vite 8 (`frontend/package.json`) requires a current Node runtime |
| **Docker Desktop** | any recent version | Runs MongoDB and ChromaDB via `infra/docker/docker-compose.yml` |
| **Git** | any recent version | — |
| **Ollama** | any recent version | Runs the local LLM backing AI Reasoning's recommendation step (see below) |
| **PlatformIO Core** | any recent version | Only needed if you're building/flashing the firmware in `firmware/` |

Ollama itself is a separate local service (like Docker), never a pip dependency and never a cloud endpoint. After installing it, pull the model the backend expects by default:

```
ollama pull llama3
```

If Ollama isn't running (or a different model is pulled), AI Reasoning automatically falls back to its rule-based recommendation logic rather than failing — see §9.

---

## 3. First-time setup

```bash
git clone <this-repo-url>
cd vidur
```

### Backend

```bash
cd backend
py -3.11 -m venv venv
venv\Scripts\activate.bat
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

`requirements.txt` pins `torch==2.13.0+cpu`, which is fetched from PyTorch's own CPU wheel index (`--extra-index-url` is already declared in the file, no extra flag needed). spaCy's pretrained pipeline is **not** pip-installable as a normal dependency, hence the separate `spacy download` step above.

Create `backend/.env` (this file is git-ignored; there is a root-level `.env.example` you can use as a starting point, but note it is stale — it predates the Ollama settings and still lists `CORS_ALLOWED_ORIGINS=["http://localhost:3000"]`, not the frontend's real dev port. Use the values below instead):

```
ENVIRONMENT=development
DEBUG=true

SECRET_KEY=<any string, 16+ characters>

MONGODB_URI=mongodb://localhost:27017
MONGODB_DB_PREFIX=vidur_project_

CHROMADB_HOST=localhost
CHROMADB_PORT=8001
CHROMADB_COLLECTION_PREFIX=vidur_project_

LOG_LEVEL=INFO
LOG_FORMAT=text
LOG_DIR=logs

CORS_ALLOWED_ORIGINS=["http://localhost:5173"]

OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama3
OLLAMA_TIMEOUT_SECONDS=120.0
```

`OLLAMA_HOST`/`OLLAMA_MODEL`/`OLLAMA_TIMEOUT_SECONDS` all have working code defaults matching the values above (see `backend/app/config/settings.py`), so they're optional in `.env` — listed here for clarity. `SECRET_KEY` and `MONGODB_URI` are the only two variables the app will refuse to start without. See §4 for the eleven `MINOR_*`/`MAJOR_*` feature-flag variables, also settable here.

If you want the Specs local agent to run, install its separate (deliberately isolated from the main app) dependency set:

```bash
pip install -r scripts\requirements-agent.txt
```

### Frontend

```bash
cd ..\frontend
npm install
```

Create `frontend/.env`:

```
VITE_API_BASE_URL=http://localhost:8080
```

(`frontend/.env.example` in the repo currently says port `8000` — that's stale relative to how the app is actually run; see §5. Point it at `8080` to match `start_vidur.bat`, or whatever port you actually launch `uvicorn` on.)

### Databases

From the repo root:

```bash
docker compose -f infra\docker\docker-compose.yml up -d
```

This starts `vidur-mongodb` (Mongo 7, port `27017`) and `vidur-chromadb` (`chromadb/chroma:1.5.9`, host port `8001` → container port `8000`), both with named, persistent volumes.

---

## 4. Feature flags reference

Every flag lives in `backend/app/config/feature_flags.py` and can be overridden by an environment variable of the same name (e.g. `MAJOR_ML_RISK_PREDICTION=true` in `backend/.env`) with zero code changes. Major-tier routes always exist and always compile — a disabled Major flag returns HTTP 403 from its route, it doesn't disappear.

| Flag | Default | Unlocks |
|---|---|---|
| `MINOR_PROJECT_INSPECTION` | `True` | The baseline static Inspection Engine |
| `MINOR_AI_REASONING` | `True` | AI Reasoning (correlation, dependency impact, debugging hypotheses, Ollama-backed recommendations) |
| `MINOR_REQUIREMENT_CONSISTENCY` | `True` | Requirement-to-implementation consistency checking (part of NLP) |
| `MINOR_ARCHITECTURE_CONSISTENCY` | `True` | Architecture-consistency checking |
| `MINOR_PROJECT_MEMORY` | `True` | Persistent inspection/finding history in Mongo, trend endpoints |
| `MINOR_BASIC_ANALYTICS` | `True` | Baseline analytics surfaced through Memory's trend endpoints |
| `MAJOR_DEEP_LEARNING_VISUAL_INSPECTION` | `False` | The Deep Learning Vision engine (OpenCLIP/OpenCV screenshot comparison) |
| `MAJOR_ML_RISK_PREDICTION` | `False` | The ML Prediction engine (regression risk, technical debt, failure probability, high-risk modules, scikit-learn quality trend) |
| `MAJOR_IOT_ENVIRONMENTAL_ANALYTICS` | `False` | All Specs raw telemetry — personal, computer, calendar, environmental ingestion/read routes |
| `MAJOR_ADVANCED_NLP_DOCUMENT_REASONING` | `False` | Reserved for advanced NLP document-reasoning capability (registered in the flag registry; not currently wired to gate a specific route — the spaCy linguistic-analysis upgrade shipped as an always-on addition under `MINOR_AI_REASONING`/`MINOR_REQUIREMENT_CONSISTENCY` instead, per the constitution's "no inventing structure beyond what's requested" rule) |
| `MAJOR_PREDICTIVE_DASHBOARDS` | `False` | The Specs ML Prediction Engine (`GET /specs/prediction`'s four outputs) |

All six `MINOR_*` flags default **on**; all five `MAJOR_*` flags default **off** — this is enforced by the constitution (Articles 41-44) and is re-verified in the test suite. Note that the checked-in `backend/.env` used for local development on this machine currently overrides `MAJOR_IOT_ENVIRONMENTAL_ANALYTICS`, `MAJOR_PREDICTIVE_DASHBOARDS`, `MAJOR_ML_RISK_PREDICTION`, and `MAJOR_DEEP_LEARNING_VISUAL_INSPECTION` to `true` for local testing — that file is git-ignored and does not affect the committed defaults above.

---

## 5. Running the app

### Option A — `start_vidur.bat` / `stop_vidur.bat` (Windows, one shot)

```
start_vidur.bat
```

This script, run from the repo root, actually:

1. Kills whatever process is currently listening on port `8080` (see the port-8080 gotcha in §9)
2. Runs `docker compose -f infra\docker\docker-compose.yml up -d` (Mongo + ChromaDB)
3. Opens a new terminal window and starts the backend: `cd backend && venv\Scripts\activate.bat && uvicorn app.main:app --port 8080`
4. Waits 3 seconds, then opens another terminal window and starts the Specs local agent: `python scripts\local_agent.py --project-id vidur-self --backend-url http://localhost:8080`
5. Opens a third terminal window and starts the frontend: `npm run dev` (Vite, port `5173`)
6. Waits 5 seconds and opens `http://localhost:5173` in your default browser
7. Pauses, waiting for you to press any key in that same window
8. On keypress: force-closes the three windows it opened (by window title) and frees port `8080` again

`stop_vidur.bat` does the cleanup half of that on its own (kill the three named windows, free port `8080`) for the case where you closed the launcher window without pressing a key first, or want to stop everything without having the launcher window open.

Both scripts assume `backend\venv\` already exists (§3) and require Docker Desktop to already be running.

### Option B — manual, multiple terminals

```bash
# Terminal 1 — databases
docker compose -f infra\docker\docker-compose.yml up -d

# Terminal 2 — backend
cd backend
venv\Scripts\activate.bat
uvicorn app.main:app --port 8080

# Terminal 3 — frontend
cd frontend
npm run dev

# Terminal 4 (optional) — Specs local agent
cd backend
venv\Scripts\activate.bat
python scripts\local_agent.py --project-id <your-project-id> --backend-url http://localhost:8080
```

Backend: `http://localhost:8080` (interactive docs at `/docs`, OpenAPI schema at `/openapi.json`). Frontend: `http://localhost:5173`.

Note: `backend/app/config/settings.py`'s `PORT` field defaults to `8000`, but nothing in this repo actually reads it to start the server — every real launch path (`start_vidur.bat`, the manual command above) passes `--port 8080` to `uvicorn` explicitly. `8080` is the port actually in use everywhere else (the frontend's `VITE_API_BASE_URL`, the local agent's `--backend-url`, CORS origins).

---

## 6. Using the app

- **Dashboard** — project health overview: DB connectivity badge, health-score trend chart, quick links.
- **Projects** — switch the active project (drives the `X-Project-Id` header sent with every subsequent request) or register a new one.
- **Inspection Reports** — runs and displays the baseline static Inspection Engine's findings for the active project.
- **AI Reasoning** — issue-correlation groups, dependency-impact assessments, debugging hypotheses, and drift insight, plus the final recommendations produced either by the local Ollama LLM or (if Ollama is unreachable) the rule-based fallback.
- **NLP** — requirement/architecture consistency findings, including spaCy-rescued paraphrase matches.
- **ML Prediction** — regression risk, technical debt, failure probability, high-risk modules, and the scikit-learn-backed quality trend; gracefully shows a 403/disabled message rather than crashing when `MAJOR_ML_RISK_PREDICTION` is off.
- **Deep Learning Vision** — upload or paste baseline/current UI screenshots (real `<input type="file">` image upload wired to the `image_bytes_base64` contract, alongside the older structured pixel/layout input path) and get back an embedding-similarity or classical-fallback comparison report; also 403-graceful when its flag is off.
- **Specs** — live-polled current-reading tiles for personal/computer/environmental metrics (each showing an explicit "Not detected" rather than a blank when a metric is missing), manual inputs for sleep hours/caffeine/deadlines, a real-time clock + day-of-week + upcoming-deadlines list, and the four-output prediction widget (upcoming-session likelihood, last-session summary, last-5-session comparison, weekly zero-filled chart).
- **Memory** — persisted inspection/prediction history and the health-score trend chart backing the Dashboard.
- **Feature Flags / Settings** — read-only view of every flag's currently resolved state.

---

## 7. Testing

### Backend

```bash
cd backend
venv\Scripts\activate.bat
pytest -q
```

Run just now against this repo: **481 passed**, 0 failed, 0 skipped, ~43s.

### Frontend

```bash
cd frontend
npm run build   # tsc -b && vite build
npm run lint    # oxlint
```

Run just now against this repo:
- `npm run build` — succeeds. Output: one advisory-only warning that the main JS chunk is over 500 kB after minification (not an error; no code-splitting has been introduced yet).
- `npm run lint` — zero errors. Three pre-existing warnings, all `react(only-export-components)` in `src/context/ProjectContext.tsx` (it exports the `useProject`/`useProjectId` hooks alongside the `ProjectProvider` component — a standard, intentional React Context pattern, not a defect).

### Firmware

Requires PlatformIO Core (`pip install platformio`, ideally into its own isolated environment separate from `backend/venv` — see the gotcha in §9). From `firmware/`:

```bash
pio run -e esp32dev
pio run -e uno
pio run -e nanoatmega328new
pio run -e megaatmega2560
```

Each target compiles as its own PlatformIO environment; see §8 for their verified status.

---

## 8. IoT / firmware status

`firmware/platformio.ini` defines four board environments from one shared `firmware/src/main.cpp` codebase:

| PlatformIO environment | Board | `IDENTIFY` ID |
|---|---|---|
| `esp32dev` | ESP32 dev board | `esp32` |
| `uno` | Arduino Uno | `uno` |
| `nanoatmega328new` | Arduino Nano (new bootloader, ATmega328) | `nano` |
| `megaatmega2560` | Arduino Mega 2560 | `mega2560` |

All four read a DHT22 (temperature/humidity), a BH1750 (ambient light), and an analog sound sensor, and implement the exact `READ`/`IDENTIFY` line-based protocol in [`docs/specs/serial-protocol.md`](docs/specs/serial-protocol.md), so `backend/scripts/local_agent.py`'s hardware auto-detection needs zero changes once real hardware exists.

**Status: compile-verified only, for all four targets — explicitly not verified against physical hardware for any of them.** No physical ESP32/Uno/Nano/Mega, DHT22, BH1750, or sound sensor module has been available during development. This is tracked as the one open item in `docs/tracker/development-tracker.md`, blocked on hardware acquisition rather than any known code issue.

---

## 9. Common gotchas

These are real issues hit and fixed during this project's development, documented in `docs/tracker/development-tracker.md` and reflected directly in the code referenced below — plus a couple of standard setup issues for this exact stack that are worth knowing about up front.

- **Port 8080 already bound (Windows).** A previous backend process that wasn't cleanly shut down (e.g. the launcher terminal was closed directly instead of stopped via `stop_vidur.bat`) can leave `uvicorn` still holding port `8080`, so the next `start_vidur.bat` run fails to bind. Both `start_vidur.bat` and `stop_vidur.bat` handle this automatically: `for /f "tokens=5" %%a in ('netstat -aon ^| find ":8080" ^| find "LISTENING"') do taskkill /F /PID %%a`. If you're running the backend manually and hit `[Errno 10048]`/an "address already in use" error (or the related Windows socket error `WinError 10013`, which can surface if a stale process still has the port in a not-fully-released state), run that same `netstat`/`taskkill` sequence yourself, or just run `stop_vidur.bat` first.
- **ChromaDB client/server version mismatch.** `requirements.txt` pins the `chromadb` **client** library to `1.5.9`; if `infra/docker/docker-compose.yml`'s ChromaDB **server** image is pinned to an older major version (this repo hit it with `0.5.5`), the client's `HttpClient` targets `/api/v2/*` endpoints the old server doesn't serve, and the Dashboard's DB-health badge reports ChromaDB as down. Fix: keep the compose file's `chromadb/chroma:` image tag matching the pinned client version exactly (currently `1.5.9`, already done in this repo) and use `vidur_chroma_data:/data` as the volume mount path (the `1.x` image's real persist path — an older compose file pointing at `/chroma/chroma`, the `0.5.x` path, would silently not persist anything across container recreation).
- **`.gitignore` entries wrapped in quotes don't work.** A pattern like `"running command.txt"` (with literal double quotes) in `.gitignore` is **not** the same as `running command.txt` — git does not strip the quotes, so the pattern silently matches nothing and the file keeps showing up as untracked. Use unquoted patterns.
- **`git add` scoped from a subdirectory.** Running `git add` from inside `backend/` or `frontend/` only stages paths under that subtree; a broad `git add -A`/`git add .` run from the wrong directory is how personal scratch files (`running command.txt`, `tommorow work.txt`) ended up committed once in this repo's history. Run `git status` from the repo root and add specific paths rather than relying on a broad add from an arbitrary working directory.
- **Docker Desktop installed but not running.** `docker compose -f infra\docker\docker-compose.yml up -d` (and therefore `start_vidur.bat`) needs the Docker Desktop application/engine actually running first, not just installed — otherwise the command fails immediately with a daemon-connection error. Start Docker Desktop and wait for it to report "running" before launching VIDUR.
- **venv not activated.** `pip install`/`python -m py_compile`/`pytest`/`uvicorn` run against your system Python (and its packages, if any) if `backend\venv\Scripts\activate.bat` wasn't run first in that terminal — symptoms are usually `ModuleNotFoundError` for a package you know is installed, or an unexpectedly different `chromadb`/`spacy`/`numpy` version being picked up. Always confirm with `where python` (should point inside `backend\venv\`) before troubleshooting further.
- **Ollama not running.** AI Reasoning's `OllamaClient` treats "connection refused", "timeout", and "malformed response" identically: it raises `OllamaUnavailableError`, and `AIReasoningEngine` automatically falls back to the pre-existing rule-based `RecommendationEngine` rather than failing the request. You'll still get recommendations with Ollama stopped — just not LLM-authored ones. Run `ollama list` to confirm `llama3:latest` (or whatever `OLLAMA_MODEL` you configured) is actually pulled if you expect the LLM path to be used.

---

## 10. Project status

VIDUR's original 11-module plan (Core Config → Project Isolation → DB Layer → Inspection Engine → AI Reasoning → NLP → ML Prediction → Deep Learning Vision → Memory → API Layer → Frontend Dashboard) is complete, plus the Specs backend/local-agent/ML-prediction/frontend modules, the Real AI/ML/DL/NLP Upgrade (Ollama, spaCy, scikit-learn, OpenCLIP/OpenCV — all four clauses implemented and verified), and IoT firmware for all four required board targets (compile-verified, pending hardware).

For exactly what's done, what's open, and the full verification history behind every claim above, see the live log: [`docs/tracker/development-tracker.md`](docs/tracker/development-tracker.md).

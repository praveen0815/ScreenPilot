# ScreenPilot

ScreenPilot is a **production-oriented AI agent platform** for planning and executing user tasks with a **safety-first** tool layer: JWT-authenticated APIs, human approval for risky actions, a deterministic workflow engine, structured memory, and a React dashboard with **real-time task events**.

The default stack uses a **mock LLM** for reproducible demos and tests. Browser, desktop, and vision adapters are **optional** and gated by environment flags.

## Features

| Area | Capability |
|------|------------|
| **Auth** | Register/login, Argon2 passwords, JWT access + rotating refresh tokens |
| **Tasks** | Create, run, pause, resume, cancel; user-scoped persistence |
| **Agent** | LangGraph orchestration: interpret → plan → validate → approval → workflow execution |
| **Tools** | Registry with permissions, timeouts, safe calculator, text transform, mock + browser/desktop/vision tools |
| **Safety** | Risk tiers, injection blocking, confirmation gates, approval workflows, audit logs |
| **Workflow** | Multi-step runs, retries, conditionals, pause/resume, idempotency keys |
| **Memory** | Conversation, checkpoints, summaries, preferences, retention |
| **Realtime** | WebSocket + REST task events (13 event types), persisted ordering |
| **Frontend** | Dashboard, chat, task detail, approvals, settings, live event timeline |
| **Ops** | `/health`, `/ready`, structured JSON logs, request IDs, Docker Compose |

## Architecture

```mermaid
flowchart TB
  subgraph Client
    UI[React / Vite UI]
    WS[WebSocket client]
  end

  subgraph API[FastAPI]
    R[Routes + middleware]
    O[Agent orchestrator]
    G[LangGraph]
    W[Workflow engine]
    E[Event broker]
  end

  subgraph Data
    PG[(PostgreSQL)]
    RD[(Redis)]
  end

  subgraph Engines
    LLM[LLM provider - mock default]
    TR[Tool registry + executor]
    BR[Browser / Playwright]
    DT[Desktop adapter]
    VS[Vision / OCR]
  end

  UI --> R
  WS --> R
  R --> O --> G --> W
  W --> TR
  TR --> BR
  TR --> DT
  TR --> VS
  G --> LLM
  O --> PG
  W --> PG
  E --> PG
  R --> RD
```

Deeper design notes: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Tech stack

| Layer | Technologies |
|-------|----------------|
| Backend | Python 3.12, FastAPI, SQLAlchemy 2 (async), Alembic, LangGraph |
| Data | PostgreSQL 16, Redis 7 |
| Auth | Argon2, PyJWT |
| Automation | Playwright (optional), PyAutoGUI / mock desktop, mock/tesseract vision |
| Frontend | React 19, TypeScript, Vite 8, Tailwind 4, React Router |
| Deploy | Docker Compose (API + nginx frontend + Postgres + Redis) |

## Project structure

```
ScreenPilot/
├── backend/           # FastAPI app, Alembic, pytest (116 tests)
├── frontend/          # React dashboard, Vitest (10 tests)
├── docs/              # Architecture, test report, release audit
├── docker-compose.yml
├── .env.example       # Template only — never commit .env
└── README.md
```

## Prerequisites

- **Python 3.12+**
- **Node.js 20+** (24 used in Docker frontend build)
- **Docker & Docker Compose** (recommended full stack)
- **Playwright Chromium** (optional; only for browser automation tests/runtime)

## Environment setup

```powershell
copy .env.example .env
```

Set at minimum:

- `JWT_SECRET` — at least 32 characters (required in Docker via `${JWT_SECRET:?...}`)
- `POSTGRES_PASSWORD` when using Compose Postgres
- `DATABASE_URL` must use driver `postgresql+asyncpg://`

See [.env.example](.env.example) for browser, desktop, vision, workflow, and memory toggles.

## Docker setup

```powershell
docker compose config    # validate compose file
docker compose up --build
```

| Service | URL |
|---------|-----|
| API | http://localhost:8000 |
| OpenAPI | http://localhost:8000/docs |
| Web (nginx) | http://localhost:8080 |

The backend container runs `alembic upgrade head` then Uvicorn (`app/bootstrap.py`).

**Docker verification (Phase 15):** `docker compose config` valid; **backend** and **frontend** images build successfully on this machine (2026-11-24). Full `docker compose up` smoke test was not automated in this phase—run locally after setting `.env`.

## Local development

### Infrastructure only

```powershell
docker compose up postgres redis
```

### Backend

```powershell
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
$env:DATABASE_URL="postgresql+asyncpg://screenpilot:YOUR_PASSWORD@localhost:5432/screenpilot"
$env:REDIS_URL="redis://localhost:6379/0"
$env:JWT_SECRET="your-local-dev-secret-at-least-32-chars"
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

### Frontend

```powershell
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 (Vite proxies `/api`, `/health`, `/ready` to port 8000).

## API overview

Interactive docs: **http://localhost:8000/docs**

| Group | Examples |
|-------|----------|
| System | `GET /health`, `GET /ready`, `GET /api/capabilities` |
| Auth | `POST /api/auth/register`, `/login`, `/refresh`, `/logout` |
| User | `GET/PATCH /api/users/me`, preferences |
| Tasks | `POST/GET /api/tasks`, `/{id}/run`, `/resume`, `/cancel` |
| Approvals | `GET /api/tasks/{id}/approvals`, approve/reject |
| Agent | `POST /api/agent/runs` (auth required) |
| Tools | `GET /api/tools` |
| Memory | `GET /api/tasks/{id}/memory` |
| Events | `GET /api/tasks/{id}/events`, `WS /api/ws/events?token=&task_id=` |

All protected routes require `Authorization: Bearer <access_token>` except WebSocket (token in query string).

## Testing

```powershell
# Backend (SQLite in-memory for most tests)
cd backend
pytest -q
# 112 passed, 4 skipped (last run 2026-11-24)

# Browser-marked tests (requires Playwright)
pytest -q -m browser

# Frontend
cd frontend
npm test
npm run build
# 10 passed (last run 2026-11-24)
```

Details: [docs/PHASE13_TEST_COVERAGE_REPORT.md](docs/PHASE13_TEST_COVERAGE_REPORT.md).

## Security

- User-scoped tasks, approvals, and events; cross-user access returns 404/403.
- Tool safety gateway blocks secret fields and prompt-injection patterns in arguments.
- Browser URL policy blocks dangerous schemes and (in production) localhost unless allowed.
- Event payloads and logs sanitize secret-like keys/values.
- **Not implemented:** HTTP rate limiting (documented in Phase 13 security tests).

More: [docs/PHASE15_FINAL_RELEASE_REPORT.md](docs/PHASE15_FINAL_RELEASE_REPORT.md#security-validation-summary).

## Demo workflow (mock LLM)

1. Register at `/login` in the UI (or via API).
2. Create a task: *"Summarize the weekly status report"* → **Run** → completes with mock plan (`tool.app_status`, `tool.text_transform`).
3. Calculator E2E keyword: instruction containing **`e2e-calculator`**.
4. Risk demo: instruction with **`purchase`** → awaits approval → approve or reject on task/approvals pages.
5. Open task **Timeline** tab for live WebSocket events (or poll fallback when disconnected).
6. Optional browser demo: set `BROWSER_ENABLED=true`, `BROWSER_ALLOW_LOCALHOST=true`, install Playwright; use instruction **`e2e-browser`** with a `http://127.0.0.1:...` URL in text (see Phase 13 E2E tests).

## Screenshots

Add portfolio images under `docs/screenshots/` (not committed with real user data):

| Suggested capture | File name |
|-------------------|-----------|
| Dashboard / task list | `dashboard.png` |
| Task detail + plan steps | `task-detail.png` |
| Approval card | `approvals.png` |
| Realtime event timeline | `events-timeline.png` |

Reference them in your README or portfolio with relative paths only.

## Limitations

| Item | Status |
|------|--------|
| Real LLM (OpenAI, etc.) | Not wired; `LLM_PROVIDER=mock` only |
| Rate limiting | Not implemented |
| Redis in app logic | Used for readiness checks; not primary event bus |
| Playwright in Docker | Not enabled by default in backend image |
| Multi-tenant admin UI | Role exists; limited admin surfaces |

Full audit: [docs/PHASE15_FINAL_RELEASE_REPORT.md](docs/PHASE15_FINAL_RELEASE_REPORT.md).

## Documentation index

| Document | Purpose |
|----------|---------|
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System design (current) |
| [docs/PHASE13_TEST_COVERAGE_REPORT.md](docs/PHASE13_TEST_COVERAGE_REPORT.md) | Tests & security matrix |
| [docs/PHASE15_FINAL_RELEASE_REPORT.md](docs/PHASE15_FINAL_RELEASE_REPORT.md) | Release audit & portfolio |
| [docs/PORTFOLIO.md](docs/PORTFOLIO.md) | Interview / resume narrative |
| [docs/GITHUB_RELEASE_CHECKLIST.md](docs/GITHUB_RELEASE_CHECKLIST.md) | Publish checklist |

## License

Specify license in repository settings if not yet added (`LICENSE` file).

## Version

Recommended tag for this milestone: **`v0.15.0`** (portfolio / phase 15 release). See GitHub checklist for steps.
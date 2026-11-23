# ScreenPilot architecture

ScreenPilot is a monorepo with a FastAPI backend and a React frontend. Phase 1 lays down configuration, health and readiness probes, migration wiring, and typed boundaries for the agent runtime and automation engines. It does not plan tasks, call an LLM, or perform browser or desktop actions.

## Layers

```
┌─────────────────────────────────────────────────────────────┐
│  frontend/ — React UI (status, future task surfaces)       │
└──────────────────────────────┬──────────────────────────────┘
                               │ HTTP
┌──────────────────────────────▼──────────────────────────────┐
│  app/api — routes, middleware, error envelopes              │
├─────────────────────────────────────────────────────────────┤
│  app/schemas — request and response contracts               │
├─────────────────────────────────────────────────────────────┤
│  app/core — settings, structured logging                    │
├─────────────────────────────────────────────────────────────┤
│  app/db — async SQLAlchemy engine, dependency checks        │
├─────────────────────────────────────────────────────────────┤
│  app/agent — LangGraph integration boundary (no graph yet)  │
│  app/tools — registry and executor gate (no tools yet)      │
│  app/automation — browser, desktop, vision contracts        │
│  app/safety — confirmation rules, untrusted observations    │
└─────────────────────────────────────────────────────────────┘
         │                              │
         ▼                              ▼
   PostgreSQL                        Redis
```

## API surface (Phase 1)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | Process liveness (no dependency checks) |
| GET | `/ready` | Readiness: Postgres and Redis probes |
| GET | `/api/capabilities` | Lists agent and automation engines as unavailable |
| POST | `/api/agent/runs` | Validates an instruction, returns 501 |

All error responses use a stable JSON envelope: `{"error": {"code", "message", "details?"}}`.

## Future integration points

### LangGraph (`app/agent/boundary.py`)

Later phases compile a LangGraph workflow in this module only. The `AgentRuntime` protocol in `app/agent/contracts.py` is what the API and task service will call. Phase 1 imports no LangGraph package.

### Tools (`app/tools/`)

- `Tool` protocol: validate arguments, execute with a `ToolContext` that carries `task_id` and `confirmed`.
- `ToolRegistry`: register approved tools by name.
- `ToolExecutor`: execution gate; Phase 1 refuses every call.

### Browser automation (`app/automation/browser.py`)

Playwright will implement `BrowserAutomationUnavailable`’s successor. `BrowserCommand` constrains allowed actions and rejects shell fields and non-http(s) navigation URLs.

### Desktop automation (`app/automation/desktop.py`)

PyAutoGUI (or a thin adapter) will implement the desktop engine. Commands have no shell or script fields.

### Vision and OCR (`app/automation/vision.py`)

OCR and vision-model adapters will implement `extract_text` and `answer`. Phase 1 only defines image and question payloads.

### Safety

- `requires_confirmation` flags high-risk tools and sensitive categories (purchase, send message, delete file, sensitive form submit, irreversible).
- `UntrustedObservation` wraps page and screen content so future prompts treat it as data, not instructions.

## Data and migrations

`app/db/base.py` defines the declarative base. Alembic revision `0001_baseline` is an empty chain head so later phases can add tables without re-initializing migrations.

## Testing strategy

- Backend: pytest with FastAPI `TestClient`; dependency checks use closed ports in tests.
- Frontend: Vitest and Testing Library on the status UI; no fabricated API success in default app code.

## Phase 2 — persistence and authentication

| Layer | Responsibility |
|-------|----------------|
| `app/db/models` | `User`, `RefreshToken`, `AgentTask`, `TaskStep`, `AgentExecution`, `ToolExecution`, `ApprovalRequest`, `AuditLog` |
| `app/auth` | Argon2 passwords, JWT access tokens, hashed refresh-token rotation |
| `app/services` | Register/login, profile updates, user-scoped tasks, audit entries |
| `app/api/routes/auth` | `/api/auth/*` |
| `app/api/routes/users` | `/api/users/me` |
| `app/api/routes/tasks` | `/api/tasks` (owner-scoped) |

Access tokens are short-lived; refresh tokens are stored hashed in PostgreSQL and rotated on each refresh. Task list/detail queries always filter by `user_id` (admins may access any task via `can_access_task`).

Alembic head: `0002_phase2_auth_and_tasks`.

## Phase 3 — LangGraph agent core (mock LLM)

| Component | Role |
|-----------|------|
| `app/agent/graph.py` | Compiled LangGraph: cancel check → interpret → plan → validate → persist → approval → mock execute |
| `app/agent/orchestrator.py` | API-facing run/cancel/approve/resume |
| `app/agent/llm/mock.py` | **Mock only** structured intent + plan (not a real model API) |
| `app/agent/llm/factory.py` | Provider selection (`LLM_PROVIDER=mock`; other providers return 501) |
| `app/tools/mock_executor.py` | Executes `mock.observe` / `mock.summarize` only |

Task statuses: `pending`, `planning`, `awaiting_approval`, `running`, `paused`, `completed`, `failed`, `cancelled`.

Alembic head: `0003_agent_plan_fields`.

## Explicit non-goals (still)

- Real OpenAI/Anthropic/etc. LLM adapters (not enabled)
- Playwright, PyAutoGUI, OCR, or vision inference
- Autonomous replanning or multi-iteration tool loops beyond the fixed mock plan
# ScreenPilot architecture (current)

Monorepo: **FastAPI** backend + **React** frontend. Phases 1–13 delivered auth, agent orchestration, tools, automation boundaries, memory, safety, workflow, realtime events, dashboard UI, and a broad pytest/Vitest suite.

## Layer diagram

```
┌──────────────────────────────────────────────────────────────────┐
│  frontend/ — React router, auth context, task UI, WS event hook    │
└───────────────────────────────┬──────────────────────────────────┘
                                │ HTTP / WebSocket
┌───────────────────────────────▼──────────────────────────────────┐
│  app/api — routes, request IDs, JSON logging, error envelopes       │
├──────────────────────────────────────────────────────────────────┤
│  app/auth — Argon2, JWT, permissions, task access deps            │
├──────────────────────────────────────────────────────────────────┤
│  app/agent — LangGraph graph, orchestrator, mock/real LLM factory │
├──────────────────────────────────────────────────────────────────┤
│  app/workflow — engine, conditions, retries, workflow state JSON   │
├──────────────────────────────────────────────────────────────────┤
│  app/tools — registry, executor, safe + browser/desktop/vision    │
├──────────────────────────────────────────────────────────────────┤
│  app/safety — gateway, approvals, risk, injection, audit           │
├──────────────────────────────────────────────────────────────────┤
│  app/memory — scoped stores, planning context, retention           │
├──────────────────────────────────────────────────────────────────┤
│  app/events — task event schema, broker, persistence               │
├──────────────────────────────────────────────────────────────────┤
│  app/automation — Playwright browser, desktop adapter, vision OCR  │
├──────────────────────────────────────────────────────────────────┤
│  app/db — SQLAlchemy models, async session, Alembic               │
└───────────────────────────────┬──────────────────────────────────┘
                                │
                    PostgreSQL ◄┴► Redis (readiness)
```

## Agent workflow (LangGraph)

1. **check_cancel** — honor `cancel_requested`
2. **interpret** — mock/real LLM → `TaskIntent`
3. **plan** — structured `TaskPlan` with tool steps
4. **validate** — schema + safety (forbidden fields)
5. **persist_plan** — steps in DB, memory checkpoint, approval rows
6. **approval_gate** — block or continue on pending/denied approvals
7. **execute** — `WorkflowEngine` runs steps with tool executor

Resume paths: after approval or after pause (`resume_from_pause`).

## Workflow engine

- Resolves step order and dependencies
- Retries, timeouts, conditional branches (`run_when`)
- Pause/cancel checkpoints in `workflow_state_json`
- Emits task/step/tool events through `publish_task_event`
- Budget: `WORKFLOW_MAX_EXECUTIONS_PER_RUN`

## Tool registry

Categories:

- **Safe tools** — `tool.calculate`, `tool.app_status`, `tool.text_transform`, `tool.current_time`
- **Mock tools** — planning/observation/workflow probes
- **Browser** — session, navigate, DOM actions (Playwright when enabled)
- **Desktop** — mouse/keyboard/screenshot (mock or PyAutoGUI)
- **Vision** — OCR/screen understanding (mock or tesseract)

Execution flows through `ToolExecutorService` → safety gateway → tool implementation.

## Realtime events

- Persisted `task_events` table (Alembic `0007_phase12_task_events`)
- In-process broker fans out to authenticated WebSocket subscribers
- REST replay: `GET /api/tasks/{id}/events?after_sequence=`

## Data model (Alembic head)

**Head revision:** `0007_phase12_task_events`

| Revision | Theme |
|----------|--------|
| 0001 | Baseline |
| 0002 | Auth + tasks |
| 0003 | Agent plan fields |
| 0004 | Memory |
| 0005 | Safety + approvals |
| 0006 | Workflow state |
| 0007 | Task events |

## Frontend surfaces

| Route | Purpose |
|-------|---------|
| `/` | Dashboard |
| `/chat` | Agent chat entry |
| `/tasks`, `/tasks/:id` | History + detail (timeline, tools, approvals) |
| `/approvals` | Pending approvals |
| `/settings`, `/profile` | Preferences + profile |
| `/login` | Auth |

## Configuration highlights

See root `.env.example`. Critical flags:

- `LLM_PROVIDER=mock` (default)
- `BROWSER_ENABLED`, `BROWSER_ALLOW_LOCALHOST`
- `DESKTOP_ENABLED`, `DESKTOP_ADAPTER`
- `VISION_ENABLED`, `VISION_OCR_PROVIDER`

## Testing boundaries

- **Default pytest:** SQLite memory DB, mock LLM, no external Postgres
- **`@integration`:** live PostgreSQL
- **`@browser`:** Playwright Chromium
- **`@e2e` / `@security`:** Phase 13 controlled scenarios

## Explicit non-goals

- Production LLM vendor integration
- Distributed event bus (Redis pub/sub for events)
- HTTP rate limiting
- Hosted multi-region deployment manifests beyond Compose
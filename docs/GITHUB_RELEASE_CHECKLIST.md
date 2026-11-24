# GitHub release checklist

Do **not** commit secrets. Do **not** push unless you intend to publish.

## Pre-commit: `.gitignore` review

Ensure ignored:

- `.env` (never commit)
- `.venv/`, `node_modules/`, `dist/`, `frontend/dist/`
- `.pytest_cache/`, `__pycache__/`, `*.egg-info/`
- Local IDE folders (`.idea/`, `.vscode/`)

Optional add (recommended before release commit):

- `backend/screenpilot_backend.egg-info/`

## Clean commit recommendations

Git currently has many **untracked** phase artifacts. Suggested commit series (squash later if desired):

1. **Backend workflow + events** — `app/workflow/`, `app/events/`, migrations 0006–0007, instrumented graph/executor
2. **Frontend dashboard** — `frontend/src/pages`, components, auth, API client, hooks
3. **Tests & docs** — `test_*phase*`, `docs/PHASE13_*`, `docs/PHASE15_*`, README, ARCHITECTURE
4. **Config** — `.env.example`, `pyproject.toml` markers, Dockerfiles if changed

Exclude from every commit:

- `.env`, credentials, `node_modules`, build artifacts, pytest cache

Example staging (PowerShell, adjust paths):

```powershell
git status
git add README.md docs/ .env.example backend/app backend/tests frontend/src
git add backend/alembic/versions/0006_phase10_workflow.py backend/alembic/versions/0007_phase12_task_events.py
# Review diff before commit:
git diff --cached --stat
```

## Repository metadata (GitHub UI)

**Description (short):**

> Safety-first AI task agent — FastAPI, LangGraph, React dashboard, approvals, workflow engine, realtime events.

**Suggested topics:**

`fastapi` `langgraph` `react` `typescript` `postgresql` `docker` `playwright` `ai-agent` `human-in-the-loop` `websocket`

**Website:** (optional) link to demo video or portfolio page

## Version tag recommendation

| Tag | Meaning |
|-----|---------|
| **`v0.15.0`** | Portfolio / documentation milestone (recommended now) |
| `v1.0.0` | Reserve for first production LLM + hardened deploy |

```powershell
git tag -a v0.15.0 -m "Phase 15: release audit, docs, test suite through phase 13"
# git push origin v0.15.0   # only when ready — NOT automatic
```

## Release checklist

- [ ] All intended files staged; no `.env`
- [ ] `cd backend && pytest -q`
- [ ] `cd frontend && npm test && npm run build`
- [ ] `docker compose config` and optional `docker compose up --build` smoke
- [ ] README screenshots placeholders or sanitized images in `docs/screenshots/`
- [ ] Create GitHub **Release** from tag `v0.15.0` with notes from `PHASE15_FINAL_RELEASE_REPORT.md`
- [ ] Attach **test result summary** (112 + 10 passes) — not fabricated coverage %

## Post-release

- [ ] Pin dependency versions if publishing to recruiters
- [ ] Add `LICENSE` (MIT/Apache-2.0) if open-sourcing
- [ ] Optional: GitHub Actions workflow for pytest on push (not included in Phase 15)
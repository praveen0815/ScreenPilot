# ScreenPilot Phase 13 — Test Coverage & Reliability Report

Generated after audit-first expansion (no wholesale rewrites). All pass/fail counts below come from executed runs noted at the end.

## Executive summary

| Layer | Test files | Role |
|-------|------------|------|
| Backend unit/integration | 28 modules under `backend/tests/` (116 collected) | API, agent, tools, safety, workflow, events, E2E, security |
| Frontend (Vitest) | 6 suites / 10 tests under `frontend/src/` | Auth client, components, realtime hook, app shell |
| Real external services | `integration`, `browser` markers | PostgreSQL, Playwright — skipped when unavailable |

## Backend coverage map

| Area | Primary modules | Notes |
|------|-----------------|-------|
| Unit | `test_config.py`, `test_safety.py`, `test_permissions.py`, `test_automation_contracts.py` | Pure logic |
| API / auth | `test_auth.py`, `test_errors.py`, `test_health.py`, `test_readiness.py`, `test_capabilities.py` | HTTP envelope, JWT |
| Database | `test_migrations.py`, `test_integration_postgres.py` (`@integration`) | Alembic head; live Postgres optional |
| Agent / planner | `test_agent_core.py`, `test_agent_boundary.py`, `test_e2e_phase13.py` | Mock LLM only in CI default |
| Tools / registry | `test_tool_framework.py` | Calculator, timeouts, permissions |
| Browser | `test_browser_policy.py`, `test_browser_integration.py` (`@browser`) | SSRF/URL policy; Playwright optional |
| Desktop | `test_desktop_engine.py` | Mock adapter + cancellation |
| Vision | `test_vision_engine.py` | Mock provider |
| Memory | `test_memory.py` | Preferences, retention |
| Safety / approval | `test_safety_phase9.py`, `test_security_phase13.py` | Gateway, approvals, injection |
| Workflow | `test_workflow_phase10.py`, `test_e2e_phase13.py` | Retry, pause, cancel |
| Realtime | `test_events_phase12.py` | REST + WebSocket |
| E2E (controlled) | `test_e2e_phase13.py` (`@e2e`) | 12 scenarios via mock planner keywords |
| Security audit | `test_security_phase13.py` (`@security`) | Authz, JWT, SSRF, approval bypass |
| Meta | `test_test_matrix_phase13.py` | Ensures audited modules exist |

### Mock vs real integration

- **Default CI path**: SQLite in-memory `sqlite_app_client`, mock LLM, mock vision/desktop unless env enables real adapters.
- **`@integration`**: Requires PostgreSQL at `DATABASE_URL` (see `test_integration_postgres.py`).
- **`@browser`**: Requires Playwright Chromium (`test_browser_integration.py`, E2E scenarios 5–8).

## Frontend coverage map

| Area | File |
|------|------|
| App / auth routing | `App.test.tsx` |
| API auth headers | `api/client.test.ts` |
| Task state UI | `components/task/TaskStatusBadge.test.tsx` |
| Approvals UI | `components/approval/ApprovalCard.test.tsx` |
| Error states | `components/ui/ErrorBanner.test.tsx` |
| Realtime events | `hooks/useTaskEventStream.test.ts` |

## Controlled E2E scenarios (`test_e2e_phase13.py`)

| # | Scenario | Test |
|---|----------|------|
| 1 | User creates simple task | `test_scenario_01_user_creates_simple_task` |
| 2 | Agent generates plan | `test_scenario_02_agent_generates_plan` |
| 3–4 | Calculator tool + completion | `test_scenario_03_calculator_tool_and_04_completion_report` (`e2e-calculator`) |
| 5–8 | Browser local site + extract | `test_scenario_05_through_08_browser_task_extract_and_report` (`@browser`, `e2e-browser`) |
| 9 | Risky action → approval | `test_scenario_09_risky_action_triggers_approval` |
| 10 | Rejected approval blocks run | `test_scenario_10_rejected_approval_blocks_execution` |
| 11 | Cancellation stops task | `test_scenario_11_cancellation_stops_task` |
| 12 | Failed tool handled safely | `test_scenario_12_failed_tool_handled_safely` (`e2e-tool-fail`) |

## Security validation checklist

| Check | Status | Evidence |
|-------|--------|----------|
| Authentication | Pass | `test_auth.py`, `test_security_phase13` JWT tests |
| Authorization / cross-user | Pass | `test_task_access.py`, `test_permissions.py`, events 403 |
| JWT handling | Pass | Tamper + invalid token tests |
| Secrets in logs/events | Pass | Phase 12 sanitization + caplog checks |
| SQL injection (instruction) | Pass | Parameterized ORM; `test_sql_injection_instruction_stored_safely` |
| Input validation | Pass | Pydantic schemas; `plan-invalid` agent test |
| SSRF / unsafe URLs | Pass | `test_browser_policy.py`, metadata URL block |
| Prompt injection (tool args) | Pass | `test_safety_phase9`, gateway tests |
| Browser / desktop permissions | Pass | `test_executor_blocks_unauthorized_browser_tool`, desktop tests |
| Tool abuse / shell fields | Pass | Plan validator + gateway |
| Rate limiting | **Not implemented** | Documented in `test_rate_limiting_not_yet_implemented` |
| Task resource limits | Pass | Workflow budget settings + phase 10 tests |
| Approval bypass | Pass | Resume 409 without approval |
| Logging privacy | Pass | Agent boundary + structured HTTP logs (path only in caplog) |

## Services not required for default test run

| Service | Tests affected | Behavior when down |
|---------|----------------|-------------------|
| PostgreSQL | `test_integration_postgres.py` | Marked `@integration`; skipped or fails if run explicitly |
| Redis | `/ready` checks | `test_readiness.py` tolerates down in test env |
| Playwright Chromium | `@browser` | `pytest.skip("Playwright Chromium is not installed.")` |
| Tesseract | Vision tesseract paths | Mock provider default; optional real OCR not in default suite |

## How to run

```bash
# Backend — full default suite (SQLite)
cd backend && .venv/Scripts/python.exe -m pytest -q

# Security + E2E only
cd backend && .venv/Scripts/python.exe -m pytest -q -m "security or e2e"

# Browser scenarios (needs Playwright)
cd backend && .venv/Scripts/python.exe -m playwright install chromium
cd backend && .venv/Scripts/python.exe -m pytest -q -m browser

# Frontend
cd frontend && npm test
```

## Execution results (this phase)

| Command | Result |
|---------|--------|
| `pytest -q` (backend, default SQLite) | **112 passed**, 4 skipped, 6 warnings (2026-11-24) |
| `npm test` (frontend) | **10 passed** across 6 files (2026-11-24) |

**Skips observed:** E2E browser scenario when Playwright Chromium unavailable; `@integration` Postgres tests when service down; other environment-gated browser tests.

---

**Phase 13 stop boundary**: No new product features beyond mock planner keywords for E2E and test/documentation artifacts.
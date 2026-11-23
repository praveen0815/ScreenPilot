# ScreenPilot

Production-oriented AI desktop and computer-use agent. **Phase 1** laid down the API shell, boundaries, and Docker Compose. **Phase 2** adds PostgreSQL models, Alembic migrations, JWT authentication (Argon2 passwords, rotating refresh tokens), user profiles, and user-scoped task persistence. Autonomous execution, browser, and desktop automation remain disabled.

## Repository layout

| Path | Role |
|------|------|
| `backend/` | FastAPI application, Alembic, pytest suite |
| `frontend/` | React + TypeScript + Vite + Tailwind |
| `docs/ARCHITECTURE.md` | Layering and future integration points |
| `docker-compose.yml` | Postgres, Redis, API, web |

## Prerequisites

- Python 3.12+
- Node.js 20+ (24 tested)
- Docker and Docker Compose (for full stack)

## Configuration

```powershell
copy .env.example .env
```

Edit `.env` and set at least `POSTGRES_PASSWORD` and a strong `JWT_SECRET` (32+ characters). `DATABASE_URL` must use the `postgresql+asyncpg://` driver.

## Run with Docker Compose

```powershell
docker compose up --build
```

| Service | URL |
|---------|-----|
| API | http://localhost:8000 |
| API docs | http://localhost:8000/docs |
| Web (nginx) | http://localhost:8080 |

Check readiness:

```powershell
curl http://localhost:8000/health
curl http://localhost:8000/ready
curl http://localhost:8000/api/capabilities
```

## Local development (without Docker)

### PostgreSQL and Redis

Start dependencies yourself, or run only infra:

```powershell
docker compose up postgres redis
```

### Backend

```powershell
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
$env:DATABASE_URL="postgresql+asyncpg://screenpilot:change-me-screenpilot-db-password@localhost:5432/screenpilot"
$env:REDIS_URL="redis://localhost:6379/0"
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

### Frontend

```powershell
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. The dev server proxies API requests to port 8000.

## Tests

### Backend

```powershell
cd backend
pip install -e ".[dev]"
pytest
```

### Frontend

```powershell
cd frontend
npm install
npm run test
npm run build
```

## Auth and tasks (Phase 2)

```powershell
# Register
curl -X POST http://localhost:8000/api/auth/register -H "Content-Type: application/json" -d "{\"email\":\"you@example.com\",\"password\":\"valid-passphrase-1\",\"display_name\":\"You\"}"

# Use returned access_token as Bearer for /api/users/me and /api/tasks
```

Migrations run automatically in the backend container (`alembic upgrade head`). Locally: `cd backend` then `alembic upgrade head` with `DATABASE_URL` and `JWT_SECRET` set.

## Current limitations

- `POST /api/agent/runs` requires auth, persists a task, then returns **501** (`agent_unavailable`).
- No LangGraph execution, Playwright, PyAutoGUI, OCR, or LLM calls yet.
- Child execution rows (`TaskStep`, `AgentExecution`, etc.) exist as schema only until later phases populate them.

See `docs/ARCHITECTURE.md` for how later phases plug into the boundaries defined here.
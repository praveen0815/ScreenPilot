# 🖥️ ScreenPilot

### AI-Powered Desktop & Computer-Use Agent

ScreenPilot is a production-oriented AI desktop agent designed to evolve into an intelligent system capable of understanding user instructions, planning tasks, and interacting with desktop environments through controlled automation.

The project follows a modular architecture with a secure backend, persistent task management, authentication, and a modern web interface. It is being developed incrementally, with autonomous execution and computer-use capabilities introduced in later phases.

---

## ✨ Features

- 🔐 **Secure Authentication** — JWT-based authentication with Argon2 password hashing and rotating refresh tokens.
- 👤 **User Profiles** — Authenticated user profiles and account management.
- 📋 **Task Management** — User-scoped task creation and persistent storage.
- 🗄️ **Database Layer** — PostgreSQL with SQLAlchemy async support.
- 🔄 **Database Migrations** — Schema versioning using Alembic.
- ⚡ **API Backend** — FastAPI-based REST API.
- 🎨 **Modern Frontend** — React, TypeScript, Vite, and Tailwind CSS.
- 🐳 **Containerized Infrastructure** — Docker Compose for the application stack.
- 🧩 **Modular Architecture** — Clear boundaries for future AI agent and automation integrations.
- 🛡️ **Capability Boundaries** — Autonomous execution and computer automation remain disabled until implemented.

---

## 🏗️ Tech Stack

| Category | Technologies |
|---|---|
| Backend | Python 3.12, FastAPI |
| Frontend | React, TypeScript, Vite |
| Styling | Tailwind CSS |
| Database | PostgreSQL |
| ORM | SQLAlchemy (Async) |
| Migrations | Alembic |
| Authentication | JWT, Argon2 |
| Cache / Infrastructure | Redis |
| Testing | Pytest |
| Deployment | Docker, Docker Compose |

---

## 📐 Architecture

```text
                  ┌─────────────────────────┐
                  │     React Frontend     │
                  │   TypeScript + Vite     │
                  └────────────┬────────────┘
                               │
                               ▼
                  ┌─────────────────────────┐
                  │      FastAPI API       │
                  │ Authentication / Tasks  │
                  └────────────┬────────────┘
                               │
                 ┌─────────────┼─────────────┐
                 ▼             ▼             ▼
           PostgreSQL       Redis      Agent Layer
           Persistence      Cache       (Future)
                                           │
                                           ▼
                              Browser & Desktop Tools
                                    (Future)
```

---

## 📁 Project Structure

```text
ScreenPilot/
├── backend/
│   ├── app/
│   ├── alembic/
│   ├── tests/
│   └── ...
├── frontend/
│   ├── src/
│   ├── public/
│   └── ...
├── docs/
│   └── ARCHITECTURE.md
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## 🚀 Getting Started

### Prerequisites

- Python 3.12+
- Node.js 20+
- Docker
- Docker Compose

### 1. Clone the repository

```bash
git clone https://github.com/praveen0815/ScreenPilot.git
cd ScreenPilot
```

### 2. Configure environment variables

```bash
copy .env.example .env
```

Update `.env` and configure the required values:

- `POSTGRES_PASSWORD`
- `JWT_SECRET` (use a strong secret with at least 32 characters)
- `DATABASE_URL` (use the `postgresql+asyncpg://` driver)

### 3. Start the application

```bash
docker compose up --build
```

### 4. Access the services

| Service | URL |
|---|---|
| 🌐 Web Application | http://localhost:8080 |
| ⚙️ API | http://localhost:8000 |
| 📚 Swagger API Docs | http://localhost:8000/docs |

### 5. Verify API health

```bash
curl http://localhost:8000/health
curl http://localhost:8000/ready
curl http://localhost:8000/api/capabilities
```

---

## 💻 Local Development

### Start Infrastructure

```bash
docker compose up postgres redis
```

### Backend Setup

```powershell
cd backend

py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1

pip install -e ".[dev]"

$env:DATABASE_URL="postgresql+asyncpg://screenpilot:your-password@localhost:5432/screenpilot"
$env:REDIS_URL="redis://localhost:6379/0"

alembic upgrade head

uvicorn app.main:app --reload --port 8000
```

### Frontend Setup

Open a separate terminal:

```bash
cd frontend
npm install
npm run dev
```

Frontend development server:

```text
http://localhost:5173
```

---

## 🧪 Testing

### Backend

```bash
cd backend
pip install -e ".[dev]"
pytest
```

### Frontend

```bash
cd frontend
npm install
npm run test
npm run build
```

---

## 🔑 Authentication & Tasks

ScreenPilot supports authenticated user registration, login, profile access, and task persistence.

### Register a User

```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"you@example.com\",\"password\":\"valid-passphrase-1\",\"display_name\":\"You\"}"
```

Use the returned `access_token` as a Bearer token when accessing protected endpoints such as:

- `/api/users/me`
- `/api/tasks`

---

## 🔒 Security & Design Principles

- Authentication required for protected operations.
- Password hashing using Argon2.
- Refresh-token rotation.
- User-scoped task persistence.
- Separation between API, persistence, and future execution layers.
- Autonomous execution disabled by default during foundational development.

---

## 🎯 Vision

ScreenPilot aims to bridge the gap between AI reasoning and real-world computer interaction.

The long-term goal is to build an intelligent desktop agent that can:

- Understand natural-language instructions.
- Break complex tasks into actionable steps.
- Plan and execute workflows.
- Interact with browser and desktop applications.
- Maintain task context and execution history.
- Operate through controlled and observable automation.

---

## 👨‍💻 Author

**Praveen Kumar**

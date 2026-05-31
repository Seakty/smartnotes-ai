# SmartNotes AI — Project Context

## What this project is

SmartNotes AI is a full-stack web application that lets users write and manage personal notes.
The AI layer (Claude API) automatically summarises long notes and suggests relevant tags.
The project is built to production standards: authenticated users, persistent storage, REST API, and a deployed frontend.

## Goals

- Build a real, deployable AI-powered web app
- Practice spec-driven development and context engineering (GSD workflow)
- Produce a clean GitHub portfolio project
- Learn the full stack: FastAPI backend, React frontend, PostgreSQL database, Claude API integration

## Tech stack

### Backend

- Language: Python 3.11+
- Framework: FastAPI
- ORM: SQLAlchemy 2.0 (async)
- Database: PostgreSQL 15
- Cache / sessions: Redis 7
- Auth: JWT (python-jose) + bcrypt (passlib)
- AI: Anthropic Python SDK (claude-sonnet-4-20250514)
- Server: Uvicorn
- Env management: python-dotenv

### Frontend

- Framework: React 18 + TypeScript
- Build tool: Vite
- Styling: TailwindCSS 3
- State: Zustand
- HTTP client: Axios
- Router: React Router v6
- Rich text: TipTap editor

### DevOps

- Containers: Docker + Docker Compose
- CI/CD: GitHub Actions
- Deploy target: Railway (backend + DB) + Vercel (frontend)
- Secrets: .env files (never committed)

## Project structure

```
smartnotes-ai/
├── .gsd/                  ← Context engineering (this folder)
│   ├── project.md         ← THIS FILE — always include in AI sessions
│   ├── conventions.md     ← Code style and naming rules
│   ├── architecture.md    ← System design reference
│   ├── specs/             ← Feature specifications (one file per feature)
│   └── tasks/             ← Atomic task files for AI execution
│
├── backend/
│   ├── app/
│   │   ├── main.py        ← FastAPI app entry point
│   │   ├── config.py      ← Settings from env
│   │   ├── database.py    ← DB + Redis connection
│   │   ├── models/        ← SQLAlchemy models
│   │   ├── schemas/       ← Pydantic schemas (request/response)
│   │   ├── routes/        ← API route handlers
│   │   ├── services/      ← Business logic layer
│   │   └── middleware/    ← CORS, rate limiting
│   ├── tests/
│   ├── Dockerfile
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── components/    ← Reusable UI components
│   │   ├── pages/         ← Route-level page components
│   │   ├── store/         ← Zustand state stores
│   │   ├── api/           ← Axios API calls
│   │   ├── types/         ← TypeScript interfaces
│   │   └── main.tsx       ← App entry point
│   ├── Dockerfile
│   └── package.json
│
├── docker-compose.yml
├── docker-compose.dev.yml
└── README.md
```

## Current phase
> Phase 2 — Notes CRUD API (in progress)

## Phases overview

| Phase | Name                                     | Status         |
| ----- | ---------------------------------------- | -------------- |
| 0     | GSD Setup & context files                | ✅ Done  |
| 1     | Backend foundation (FastAPI + DB + Auth) | ✅ Done  |
| 2     | Notes CRUD API                           | 🔄 In progress |
| 3     | AI integration (Claude API)              | ⏳ Not started |
| 4     | Frontend (React)                         | ⏳ Not started |
| 5     | Polish & Deploy                          | ⏳ Not started |

## Key decisions & rationale

- **FastAPI over Django/Flask**: async by default, auto-generates OpenAPI docs, faster for API-only backends
- **SQLAlchemy async**: all DB calls are non-blocking, better performance with FastAPI
- **Zustand over Redux**: simpler, less boilerplate, sufficient for this project's state complexity
- **TipTap over plain textarea**: real rich text editor, extensible, React-native
- **JWT stored in httpOnly cookie**: more secure than localStorage
- **Redis for sessions**: fast invalidation, scales well

## What the AI assistant should always know

1. Every feature starts with a spec file in `.gsd/specs/` before any code is written
2. Every coding task starts with a task file in `.gsd/tasks/` before implementation
3. Follow `conventions.md` at all times — no exceptions
4. Business logic goes in `services/`, never directly in route handlers
5. All secrets come from environment variables — never hardcoded
6. All responses use the Pydantic schema layer — never return raw ORM objects

# UNC Course Builder

A web application to help UNC-Chapel Hill undergraduates plan semester schedules, understand degree requirements, and estimate graduation timelines.

This is an independent student project. It is not affiliated with, endorsed by, or sponsored by the University of North Carolina at Chapel Hill.

## Goals

- Search courses using public UNC academic information
- Build semester schedules with lectures, labs, and recitations
- Track degree requirements and estimate graduation timelines
- Keep private student records in the student's own browser

Initial data targets: the 2026-2027 catalog, the Spring 2027 semester, and a verified degree program for the B.S. in Computer Science.

## Status

Early development. Only the project foundation is implemented:

- Implemented: a landing page, a `GET /api/health` endpoint, and database and migration configuration
- Planned: course search, scheduling, degree requirement tracking, graduation estimates, Tar Heel Tracker import, custom courses, and an AI chatbot using public information

No academic database schema exists yet.

## Technology

- Frontend: Next.js (App Router), React, TypeScript, Tailwind CSS
- Backend: Python, FastAPI, Pydantic, SQLAlchemy, Alembic
- Database: PostgreSQL
- Data ingestion: Python, requests, Beautiful Soup
- Tooling: ESLint, Prettier, pytest, Ruff, GitHub Actions

## Repository structure

```text
frontend/    Next.js app
backend/     FastAPI app and tests
database/    Alembic migrations
ingestion/   Public data collection, independent of the API
docs/        Architecture and research notes
```

## Getting started

Prerequisites: Node.js 20.9 or newer, Python 3.11 or newer, and PostgreSQL 16 or newer (macOS: `brew install postgresql@16`).

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
uvicorn app.main:app --reload
```

The API runs at http://localhost:8000. Check http://localhost:8000/api/health.

### Frontend

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

The app runs at http://localhost:3000.

### Database

```bash
createdb unc_course_builder
cd backend
alembic upgrade head
```

Adjust `DATABASE_URL` in `backend/.env` for your local PostgreSQL user and password. There are no migrations yet.

### Ingestion

```bash
pip install -r ingestion/requirements.txt
```

## Environment configuration

- `backend/.env`: `DATABASE_URL`, `CORS_ALLOWED_ORIGINS`
- `frontend/.env.local`: `NEXT_PUBLIC_API_BASE_URL`

Copy the `.env.example` files and edit the copies. Real `.env` files are ignored by Git and must never be committed. Variables prefixed with `NEXT_PUBLIC_` are exposed to the browser, so never put secrets in them.

## Testing and linting

Backend, from `backend/`:

```bash
pytest
ruff check .
ruff format --check .
```

Frontend, from `frontend/`:

```bash
npm run lint
npm run typecheck
npm run format:check
```

Use `ruff format .` and `npm run format` to apply formatting. GitHub Actions runs these checks on pull requests and pushes to `main`.

## Contributing

- Branch from `main` using `feature/<short-name>`. Do not commit directly to `main`.
- Open a pull request and get one review before merging.
- Run the lint, format, and test commands above before opening the pull request.
- Use clear names and put documentation in this README or `docs/`.
- Keep changes focused and add tests for meaningful new behavior.

## Academic data and privacy

Academic information is gathered from publicly available UNC sources and may be incomplete or out of date. Verify schedules and degree requirements with your academic advisor and official UNC systems.

Private student records are intended to stay in the student's browser and never be sent to the backend, the database, or an AI provider. Processing Tar Heel Tracker PDFs will require a separate privacy review before it is implemented.

## License

MIT. See [LICENSE](LICENSE).

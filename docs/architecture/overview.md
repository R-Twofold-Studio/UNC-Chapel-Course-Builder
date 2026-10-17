# Architecture Overview

## Layers

- Frontend: Next.js app that calls the backend for public academic data.
- Backend: FastAPI service exposing public academic data from PostgreSQL.
- Database: PostgreSQL via SQLAlchemy, with schema changes managed by Alembic (database/migrations/).
- Ingestion: standalone Python code that retrieves, parses, normalizes, and validates public UNC data before it is loaded into the database. It is independent of the API.

## Privacy boundary

Private student records (completed courses, transfer, AP and IB credits, Tar Heel Tracker data) stay in the browser, with IndexedDB as the intended store. They are never sent to the backend, PostgreSQL, or an AI provider. The AI chatbot uses public academic information only. Tar Heel Tracker PDF processing needs a separate privacy review before implementation.

## Status

Only the health-check endpoint exists. Academic database schemas will be designed after the related research tasks.

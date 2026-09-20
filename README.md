# Repz API

Production REST API for the Repz workout logging and analytics app.

## Stack

Python 3.12, FastAPI, MySQL 8, SQLAlchemy 2 (async), Alembic, Firebase Admin, Redis, APScheduler, Docker.

## Local setup

1. Copy env and add secrets:

```bash
cp .env.example .env
```

Set `WORKOUTX_API_KEY` in `.env`. Keep the Firebase service account JSON next to the app (default path in `.env.example`). Do not commit `.env` or the service account file.

2. Start MySQL, Redis, and the API:

```bash
docker compose up --build
```

Or run the API on the host after `docker compose up mysql redis -d`:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

3. Open docs at http://localhost:8000/docs

4. Seed the exercise catalog (requires `WORKOUTX_API_KEY` and `ADMIN_API_KEY`):

```bash
curl -X POST http://localhost:8000/api/v1/admin/sync-exercises \
  -H "X-Admin-Key: change-me-admin-key"
```

## Auth

The Nuxt app authenticates with Firebase, then sends `Authorization: Bearer <Firebase ID token>` on every `/api/v1` request.

## Tests

```bash
pytest
RUN_DB_TESTS=1 pytest   # requires local MySQL matching .env
```

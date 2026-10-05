# Repz API

Production REST API for the Repz workout logging and analytics app.

## Stack

Python 3.12, FastAPI, **PostgreSQL 16**, SQLAlchemy 2 (async), Alembic, Firebase Admin, Redis, APScheduler, Docker.

## PostgreSQL setup

### Option A — Docker (recommended)

```bash
cp .env.example .env
docker compose up --build
```

The API waits for Postgres, runs Alembic migrations on startup, and serves on http://localhost:8000/docs .

### Option B — Local Postgres

1. Install PostgreSQL 16 and create a database:

```bash
createdb repz
psql -c "CREATE USER repz WITH PASSWORD 'repz';"
psql -c "GRANT ALL PRIVILEGES ON DATABASE repz TO repz;"
```

2. Copy env and point at your instance:

```bash
cp .env.example .env
# POSTGRES_HOST=localhost POSTGRES_USER=repz POSTGRES_PASSWORD=repz POSTGRES_DATABASE=repz
```

3. Install deps and run migrations + API:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload
```

Connection string (async SQLAlchemy):

`postgresql+asyncpg://repz:repz@localhost:5432/repz`

You can set `DATABASE_URL` in `.env` to override the `POSTGRES_*` fields.

### Option C — Deployed app (Neon + Render + Vercel)

Production uses Neon for Postgres, Render for this API, and Vercel for the Nuxt app. Paste the Neon connection string as `DATABASE_URL`; the API rewrites it for asyncpg and runs migrations against the direct host. Step-by-step: [DEPLOY.md](DEPLOY.md).

Local development stays on Docker Postgres. Only the deployed environment points at Neon.

## Exercise catalog (local JSON → DB)

Exercises live in PostgreSQL. The source file is `exercises.json` at the repo root (with `is_time_based`, `is_load_based`, etc.). Catalog rows are seeded **without** GIF URLs; remote `gifUrl` values in JSON are not used. Add media via the app (`POST /api/v1/exercises/{id}/gif`) or API upload.

**Seed once** (from the host, with Postgres running and `.env` pointing at that DB):

```bash
python scripts/seed_exercises.py
```

Or trigger via admin API (background job):

```bash
curl -X POST "http://localhost:8000/api/v1/admin/seed-exercises" \
  -H "X-Admin-Key: change-me-admin-key"
```

Re-run seed after updating `exercises.json`; rows upsert on `external_id`. Existing `gif_url` values (and on-disk GIFs) are preserved on re-seed.

### Exercise GIFs (local exercises-dataset)

Animation GIFs can be copied from a clone of [exercises-dataset](https://github.com/hasaneyldrm/exercises-dataset) (Gym visual media — see that repo’s `NOTICE.md`).

Repz `id` matches dataset `id` for **1,324** catalog rows. Import by id with a name sanity check; row `3533` is skipped (known id/name mismatch). Three Repz-only ids (`5202`–`5204`) have no dataset GIF.

```bash
# Clone alongside repz-server, e.g. Desktop/exercises-dataset
python scripts/import_dataset_gifs.py --dataset-root ../exercises-dataset
python scripts/import_dataset_gifs.py --dataset-root ../exercises-dataset --update-db
```

Use `--dry-run` to preview. If GIFs still look like old WorkoutX art, files were skipped on disk — re-run with **`--force`** to replace them from the dataset. Attribution notice is copied to `MEDIA_ROOT/GYM_VISUAL_NOTICE.md`.

## Auth

The Nuxt app authenticates with Firebase, then sends `Authorization: Bearer <Firebase ID token>` on every `/api/v1` request.

## Tests

```bash
pytest
RUN_DB_TESTS=1 pytest   # requires local Postgres matching .env
```

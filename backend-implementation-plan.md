# Backend Implementation Plan — Repz

## 1. Overview

A production-grade REST API powering a mobile PWA + web workout logging and
analytics app. Stack: **Python 3.12, FastAPI, MySQL 8, SQLAlchemy 2.0 (async),
Alembic, Firebase Admin SDK (auth verification), Redis (cache/rate-limit),
Celery/APScheduler (scheduled jobs), Docker.**

The `workoutX Developer Portal` API is used as the seed/source for the
exercise library (name, body part, target muscle, equipment, gif, difficulty,
instructions, etc.), synced into our own MySQL table so the app doesn't
depend on the third party at request time.

---

## 2. Architecture

```
┌─────────────┐      ┌────────────────────┐      ┌───────────────┐
│  Nuxt PWA   │────▶ │  FastAPI (REST)     │────▶ │   MySQL 8     │
│ (web/mobile)│      │  + Pydantic v2      │      │  (primary DB) │
└─────────────┘      │  + SQLAlchemy async │      └───────────────┘
       │             │  + Alembic          │
       │             └─────────┬───────────┘
       │                       │
       ▼                       ▼
┌─────────────┐      ┌────────────────────┐
│ Firebase Auth│◀────│  Redis (cache,     │
│ (ID token)   │      │  rate limit, jobs) │
└─────────────┘      └────────────────────┘
                                │
                                ▼
                      ┌────────────────────┐
                      │ workoutX API sync   │
                      │ (scheduled job)     │
                      └────────────────────┘
```

- **Auth flow**: Frontend authenticates with Firebase (email/password, Google,
  Apple). Frontend sends `Authorization: Bearer <Firebase ID token>` on every
  request. FastAPI middleware verifies the token via `firebase-admin`,
  extracts `uid`, and maps/creates a local `users` row (uid is the foreign
  key anchor — no passwords stored in our DB).
- **Stateless API**, horizontally scalable behind a load balancer / Cloud Run
  / ECS.
- **Sync job**: a scheduled task pages through `GET /v1/exercises` (with
  `limit`/`offset`, 1327 total) and upserts into our `exercises` table
  nightly, so the app always has a local, fast, filterable copy with images
  cached (see §7).

---

## 3. Tech Stack & Libraries

| Concern | Library |
|---|---|
| Web framework | `fastapi` |
| ASGI server | `uvicorn[standard]` (behind `gunicorn` in prod, `uvicorn.workers.UvicornWorker`) |
| ORM | `sqlalchemy[asyncio]` 2.0 |
| Migrations | `alembic` |
| DB driver | `aiomysql` or `asyncmy` |
| Validation/schemas | `pydantic` v2, `pydantic-settings` |
| Auth | `firebase-admin` |
| Caching / rate limit | `redis`, `fastapi-limiter` |
| Background jobs | `apscheduler` (simple) or `celery` + `redis` broker (if scale needed) |
| HTTP client (for workoutX sync) | `httpx` (async) |
| File/image handling | `Pillow` (thumbnail generation for gifs/static frames), `boto3`/`google-cloud-storage` for object storage |
| Testing | `pytest`, `pytest-asyncio`, `httpx.AsyncClient`, `factory_boy` |
| Linting/formatting | `ruff`, `black`, `mypy` |
| Logging/observability | `structlog`, `sentry-sdk` |
| Env/config | `pydantic-settings`, `.env` via `python-dotenv` |
| Password-less | N/A — Firebase handles credentials |
| Docs | Auto via FastAPI (`/docs`, `/redoc`) |

---

## 4. Database Schema (MySQL)

### Core tables

**users**
- `id` (PK, UUID/bigint autoinc)
- `firebase_uid` (unique, indexed)
- `email`, `display_name`, `avatar_url`
- `unit_preference` (kg/lb), `timezone`
- `height_cm`, `date_of_birth`, `gender` (optional, for calorie calcs)
- `created_at`, `updated_at`

**exercises** (synced from workoutX, plus our own custom ones)
- `id` (PK — reuse workoutX id where applicable, or internal UUID)
- `source` (`workoutx` | `custom`)
- `external_id` (workoutX id, nullable)
- `name`, `body_part`, `target`, `equipment`
- `secondary_muscles` (JSON array)
- `instructions` (JSON array)
- `gif_url` (mirrored to our own storage — see §7)
- `category`, `difficulty`, `mechanic`, `force`
- `met`, `calories_per_minute`
- `is_unilateral` (bool)
- `recommended_sets`, `recommended_reps`
- `movement_tags` (JSON array)
- `created_by_user_id` (nullable, for custom exercises)
- `is_time_based` (bool — true for plank, treadmill, etc.)
- `is_distance_based` (bool — true for treadmill, running, cycling)
- indexes on `body_part`, `target`, `equipment`, `name` (fulltext)

**routines**
- `id`, `user_id` (FK), `name`, `description`, `folder/category`
- `created_at`, `updated_at`, `last_used_at`

**routine_exercises**
- `id`, `routine_id` (FK), `exercise_id` (FK), `order_index`
- `target_sets`, `target_reps_range`, `rest_seconds`
- `notes`

**workout_sessions** (a logged workout instance)
- `id`, `user_id`, `routine_id` (nullable — ad-hoc workouts allowed)
- `name`, `started_at`, `ended_at`, `duration_seconds`
- `notes`, `body_weight_kg` (optional snapshot at time of workout)
- `total_volume_kg` (denormalized, computed on save)
- `created_at`

**workout_sets** (individual logged sets — the core logging table)
- `id`, `workout_session_id` (FK), `exercise_id` (FK), `set_number`
- `weight_kg`, `reps`, `rpe` (nullable, 1–10 scale, 0.5 steps)
- `duration_seconds` (for time-based exercises like plank)
- `distance_km` (for treadmill/running/cycling)
- `is_warmup` (bool), `is_completed` (bool)
- `created_at`

**personal_records** (denormalized for fast lookups / achievements)
- `id`, `user_id`, `exercise_id`, `record_type` (max_weight, max_reps, max_volume, best_1rm, longest_duration, longest_distance)
- `value`, `achieved_at`, `workout_set_id` (FK)

**body_metrics** (weight tracking over time)
- `id`, `user_id`, `date`, `weight_kg`, `body_fat_pct` (optional), `notes`

**achievements**
- `id`, `user_id`, `type` (streak_7, streak_30, pr_broken, volume_milestone, consistency_badge, etc.)
- `metadata` (JSON), `unlocked_at`

**Denormalized/materialized reporting tables** (refreshed via job or computed on read with caching):
- `daily_stats` (`user_id`, `date`, `total_volume`, `total_sets`, `duration_seconds`, `calories_est`)
- Weekly/monthly aggregates computed on the fly from `daily_stats` (cheap query), cached in Redis with short TTL.

---

## 5. Key API Endpoints (representative, not exhaustive)

### Auth / Users
- `POST /api/v1/users/sync` — create/update local profile after Firebase login
- `GET /api/v1/users/me`
- `PATCH /api/v1/users/me`

### Exercises
- `GET /api/v1/exercises?bodyPart=&target=&equipment=&search=&limit=&offset=`
- `GET /api/v1/exercises/{id}`
- `GET /api/v1/exercises/filters` — returns bodyPartList/targetList/equipmentList (cached)
- `POST /api/v1/exercises/custom` — user-created exercise

### Routines
- `GET/POST /api/v1/routines`
- `GET/PATCH/DELETE /api/v1/routines/{id}`
- `GET /api/v1/routines/{id}/last-logged` — returns last logged weight/reps/RPE per exercise in that routine, for pre-fill (feature #8)

### Workout Sessions & Sets
- `POST /api/v1/workouts` — start a session
- `PATCH /api/v1/workouts/{id}` — update/finish session
- `POST /api/v1/workouts/{id}/sets` — log a set
- `PATCH /api/v1/workouts/{id}/sets/{set_id}`
- `DELETE /api/v1/workouts/{id}/sets/{set_id}`
- `GET /api/v1/workouts` — history, paginated, filterable by date range
- `GET /api/v1/workouts/{id}`

### Body Metrics
- `GET/POST /api/v1/body-metrics`
- `GET /api/v1/body-metrics/graph?range=30d|90d|1y`

### Reports & Dashboard
- `GET /api/v1/reports/daily?date=`
- `GET /api/v1/reports/weekly?week=`
- `GET /api/v1/reports/monthly?month=`
- `GET /api/v1/reports/calendar?month=` — dates with a workout (for calendar heatmap)
- `GET /api/v1/reports/volume-graph?range=`
- `GET /api/v1/reports/muscle-distribution?range=`
- `GET /api/v1/reports/achievements`
- `GET /api/v1/reports/personal-records`

All list endpoints: cursor or offset pagination, filtering, sorting.

---

## 6. Feature-to-Backend Mapping

| Feature | Backend implementation notes |
|---|---|
| Exercise list + gif | Synced table + mirrored media (§7); full-text + filter search |
| Create routine | `routines` + `routine_exercises`, ordered |
| Log weight/reps/RPE/sets | `workout_sets` table, RPE validated 1–10 |
| Time/distance fields (treadmill, plank) | `is_time_based`/`is_distance_based` flags drive which fields the API accepts/validates per exercise |
| Daily/weekly/monthly report | Aggregation queries + Redis-cached rollups |
| Calendar view | `GET /reports/calendar` returns a set of dates with workout flags |
| Volume, duration, achievements | Computed on session save (`total_volume_kg`), achievement engine evaluates rules async after each session |
| Pre-filled last logged inputs | `GET /routines/{id}/last-logged`, queries most recent `workout_sets` per exercise for that user |
| Log weight for every routine workout | Uniform `workout_sets.weight_kg`, nullable so bodyweight-only exercises still work |
| Body weight / volume / muscle distribution graphs | Time-series endpoints returning arrays ready for charting |

---

## 7. workoutX Integration Details

- Store the API key server-side only (`.env` → `WORKOUTX_API_KEY`), **never**
  expose it to the frontend. All exercise data is served from our own DB/API.
- Sync job (APScheduler, nightly):
  1. Page through `/v1/exercises` using `limit=100&offset=N` until `total`
     reached.
  2. Upsert into `exercises` (match on `external_id`).
  3. Download each `gifUrl`, store in object storage (S3/GCS/Cloudflare R2),
     rewrite `gif_url` to our CDN URL (avoids hot-linking issues, faster
     load, works offline-friendly with PWA caching).
  4. Refresh `bodyPartList`, `targetList`, `equipmentList` caches (Redis, 24h TTL).
- Rate-limit-aware: respect `count`/`total` pagination, add retry/backoff via `httpx` + `tenacity`.
- Mark exercises like "Treadmill", "Plank", "Elliptical Machine", "Stationary Bike",
  "Skierg Machine", "Stepmill Machine" as `is_time_based`/`is_distance_based`
  via an equipment/category rule table (curated once, then manually
  adjustable by admin).

---

## 8. Security & Compliance

- Firebase ID token verification on every protected route (FastAPI dependency).
- Row-level ownership checks (`user_id` scoping) on every query — no cross-user leakage.
- Rate limiting per user/IP via Redis (`fastapi-limiter`).
- Input validation via Pydantic (RPE range, weight bounds, reps ≥ 0, etc.).
- CORS locked to the Nuxt app's domains.
- Secrets in environment variables / secret manager (never committed).
- HTTPS enforced at the load balancer/reverse proxy.
- SQL injection avoided by ORM-only queries (no raw string concatenation).
- Audit logging (structlog) for auth failures and destructive actions.

---

## 9. Project Structure

```
backend/
├── app/
│   ├── main.py
│   ├── core/            # config, security, firebase init, redis client
│   ├── db/               # session, base, migrations env
│   ├── models/            # SQLAlchemy models
│   ├── schemas/            # Pydantic request/response schemas
│   ├── api/
│   │   └── v1/
│   │       ├── routes/    # exercises.py, routines.py, workouts.py, reports.py, users.py
│   │       └── deps.py    # auth dependency, pagination deps
│   ├── services/           # business logic (routines_service, report_service, achievement_engine)
│   ├── jobs/                # workoutx_sync.py, aggregate_daily_stats.py
│   └── utils/
├── alembic/
├── tests/
├── Dockerfile
├── docker-compose.yml       # api + mysql + redis for local dev
├── requirements.txt / pyproject.toml
└── .env.example
```

---

## 10. Testing & CI/CD

- Unit tests for services (volume calc, achievement rules, RPE validation).
- Integration tests with a throwaway test MySQL DB (`pytest` fixtures + `alembic upgrade head`).
- Contract tests mocking the workoutX sync job.
- GitHub Actions: lint (`ruff`), type-check (`mypy`), test, build Docker image, deploy.
- Alembic migrations run automatically on deploy (pre-start hook).

---

## 11. Deployment Suggestions

- Containerized (Docker) → deploy on **Cloud Run**, **AWS ECS/Fargate**, or a
  simple VPS (DigitalOcean/Railway/Render) for MVP cost control.
- Managed MySQL: Cloud SQL / PlanetScale / AWS RDS.
- Managed Redis: Upstash / ElastiCache.
- Object storage for gifs/avatars: Cloudflare R2 / S3 / GCS + CDN.
- Firebase project shared between frontend (client SDK) and backend (admin SDK, server-side verification only).

---

## 12. Information Needed From You

1. Firebase project credentials (service account JSON) for the backend, and web config for the frontend.
2. Preferred cloud provider / hosting budget (affects DB, storage, deploy choice above).
3. Confirmation on units default (kg vs lb) and whether both should be user-toggleable (assumed yes).
4. Any exercises beyond the workoutX list you want as defaults (e.g. custom gym machines).
5. Whether social/sharing features (leaderboards, following friends) are in scope for v1, or a later phase.
6. Whether you want offline logging support in the PWA (log a workout with no signal, sync later) — affects backend idempotency/conflict-resolution design.

---

## 13. Suggested Build Order (Backend)

1. Project scaffold, DB models, Alembic migrations, Firebase auth middleware.
2. Exercise sync job + exercises API (read-only, filterable).
3. Routines CRUD.
4. Workout sessions + sets logging (the core loop).
5. Last-logged pre-fill endpoint.
6. Body metrics tracking.
7. Reports/aggregation endpoints (daily → weekly → monthly → calendar).
8. Personal records + achievement engine.
9. Hardening: rate limiting, caching, tests, CI/CD, deploy.

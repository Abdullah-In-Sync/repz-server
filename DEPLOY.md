# Deploy Repz

Free-tier layout:

| Piece | Host | Why |
| --- | --- | --- |
| Postgres | [Neon](https://neon.tech) | Free Postgres, no card |
| API | [Render](https://render.com) free web service | Runs the existing Dockerfile. Sleeps after 15 minutes idle; first request after that takes about a minute |
| Redis | [Upstash](https://upstash.com) | Free Redis for cache and rate limits. The API still serves if this is down |
| Frontend | [Vercel](https://vercel.com) | Nuxt. Deploy the `repz-client` repo |

Deploy from **`main`** on both repos. Render and Vercel only build what is on GitHub, so merge your work into `main` and push it before connecting the hosts.

Region: create Neon and Upstash in **AWS ap-southeast-1 (Singapore)**. The Render blueprint uses Singapore so the API sits next to the database.

## 1. Neon

1. New project, Postgres 16, region Singapore.
2. Connect → copy the **pooled** connection string (`-pooler` in the host). Leave it as Neon prints it, including `sslmode=require`.
3. That string is `DATABASE_URL`. Do not rewrite the scheme yourself.

Migrations run when the API starts. They use the direct host (the same string with `-pooler` removed).

## 2. Upstash

1. New Redis database, region Singapore, TLS on.
2. Copy the **rediss://** URL. That is `REDIS_URL`.

## 3. Render (API)

1. Push `repz-server` `main`.
2. Render dashboard → **New** → **Blueprint** → select `repz-server`. Render reads `render.yaml` (service name `repz-api`, branch `main`, free plan).
3. When it asks for secrets, set:
   - `DATABASE_URL` — Neon pooled string
   - `REDIS_URL` — Upstash `rediss://` URL
   - `FIREBASE_CREDENTIALS_JSON` — contents of the Firebase Admin SDK JSON (the file named `repz-*-firebase-adminsdk-*.json`). One line is fine. Base64 of that file also works.
4. `ADMIN_API_KEY` is generated for you. Copy it from the service’s Environment tab if you want the admin seed route.
5. Wait until `https://repz-api.onrender.com/health` returns JSON. `redis: true` means Upstash is connected. `PUBLIC_BASE_URL` is filled from Render’s own URL, so GIF links use the real host.

`CORS_ORIGIN_REGEX` already allows `https://*.vercel.app`. After you add a custom domain, append it to `CORS_ORIGINS` (comma-separated) and redeploy.

### Seed the exercise catalog

From your laptop, with the Neon URL in the environment (the API container does not need to be used for this):

```bash
cd repz-server
python -m venv .venv && source .venv/bin/activate
pip install -e .
DATABASE_URL='postgresql://…neon…' python scripts/seed_exercises.py
```

Use the same pooled string. Re-running upserts on `external_id`.

### Exercise GIFs

Render’s free instance has no persistent disk. Files under `MEDIA_ROOT` disappear on restart, so imported GIFs will not stay up. Workout logging, routines, and history do not need them. A later object-storage bucket (for example Cloudflare R2) is the way to keep animations.

## 4. Vercel (frontend)

In `repz-client`:

1. Push `main`.
2. Vercel → **Add New Project** → `repz-client`. Framework: Nuxt. Production branch: **main**. Node 22 (from `package.json` engines and `.node-version`).
3. Environment variables (Production, and Preview if you use it):

```
NUXT_PUBLIC_API_BASE=https://repz-api.onrender.com
NUXT_PUBLIC_FIREBASE_API_KEY=
NUXT_PUBLIC_FIREBASE_AUTH_DOMAIN=
NUXT_PUBLIC_FIREBASE_PROJECT_ID=
NUXT_PUBLIC_FIREBASE_STORAGE_BUCKET=
NUXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID=
NUXT_PUBLIC_FIREBASE_APP_ID=
NUXT_PUBLIC_FIREBASE_MEASUREMENT_ID=
```

Copy the Firebase values from the client `.env` you already use locally. No `NUXT_PUBLIC_` prefix on the local names you might have written by hand — Vercel must use the names above. These are baked in at build time, so change them and redeploy if the API URL changes.

4. Firebase console → Authentication → Settings → **Authorized domains** → add the Vercel host (`*.vercel.app` is not a wildcard you can type; add the real host, e.g. `repz-client.vercel.app`). Email/password and Google should already be enabled.
5. Open the Vercel URL, sign in, and load the exercise list. The first call after the API has slept can take up to a minute.

## What stays local

`docker compose up` is still the dev stack. Do not point a local `.env` at Neon unless you mean to.

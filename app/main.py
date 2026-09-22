from contextlib import asynccontextmanager
from pathlib import Path

import sentry_sdk
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.firebase import init_firebase
from app.core.logging import configure_logging, get_logger
from app.core.rate_limit import RateLimiter
from app.core.redis import close_redis, ping_redis
from app.db.migrate import run_migrations
from app.db.session import engine
from app.jobs.scheduler import start_scheduler, stop_scheduler

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    if settings.sentry_dsn:
        sentry_sdk.init(dsn=settings.sentry_dsn, traces_sample_rate=0.1)
    Path(settings.media_root, "gifs").mkdir(parents=True, exist_ok=True)
    if not settings.is_test:
        run_migrations()
        init_firebase()
        start_scheduler()
    yield
    stop_scheduler()
    await close_redis()
    await engine.dispose()


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

rate_limit = []
if settings.rate_limit_enabled and not settings.is_test:
    rate_limit = [Depends(RateLimiter(times=120, seconds=60))]

app.include_router(api_router, prefix="/api/v1", dependencies=rate_limit)


@app.get("/media/gifs/{filename}")
async def serve_exercise_gif(filename: str):
    from app.utils.media import ensure_local_gif, normalize_gif_id

    external_id = normalize_gif_id(filename)
    if not external_id:
        raise HTTPException(status_code=404, detail="Not found")
    path = await ensure_local_gif(external_id)
    if not path:
        raise HTTPException(status_code=404, detail="GIF not available")
    return FileResponse(path, media_type="image/gif")


media_root = Path(settings.media_root)
media_root.mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=str(media_root)), name="media")


@app.get("/health")
async def health() -> dict:
    redis_ok = await ping_redis()
    return {
        "status": "ok" if redis_ok else "degraded",
        "app": settings.app_name,
        "redis": redis_ok,
    }

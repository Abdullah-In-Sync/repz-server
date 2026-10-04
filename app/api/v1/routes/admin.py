from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, Query

from app.api.v1.deps import require_admin
from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.redis import cache_delete
from app.db.session import SessionLocal
from app.services.exercise_seed import seed_exercises_from_file

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])
logger = get_logger(__name__)


async def _run_seed(path: Path, download_gifs: bool) -> None:
    async with SessionLocal() as db:
        try:
            await seed_exercises_from_file(db, path, download_gifs=download_gifs)
            await cache_delete("exercises:filters")
        except Exception as exc:
            logger.exception("exercise_seed_failed", error=str(exc))


@router.post("/seed-exercises")
async def trigger_seed(
    background_tasks: BackgroundTasks,
    download_gifs: bool = Query(default=False),
) -> dict:
    settings = get_settings()
    path = Path(settings.exercises_json_path)
    if not path.is_file():
        return {"status": "error", "detail": f"Missing catalog file: {path}"}
    background_tasks.add_task(_run_seed, path, download_gifs)
    logger.info("exercise_seed_triggered", path=str(path), download_gifs=download_gifs)
    return {"status": "started", "path": str(path), "download_gifs": download_gifs}

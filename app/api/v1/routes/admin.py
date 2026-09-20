from fastapi import APIRouter, BackgroundTasks, Depends

from app.api.v1.deps import require_admin
from app.core.logging import get_logger
from app.db.session import SessionLocal
from app.jobs.workoutx_sync import sync_exercises

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])
logger = get_logger(__name__)


async def _run() -> None:
    async with SessionLocal() as db:
        await sync_exercises(db)


@router.post("/sync-exercises")
async def trigger_sync(background_tasks: BackgroundTasks) -> dict:
    background_tasks.add_task(_run)
    logger.info("exercise_sync_triggered")
    return {"status": "started"}

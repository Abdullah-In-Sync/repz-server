from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.core.logging import get_logger
from app.db.session import SessionLocal
from app.jobs.aggregate_daily_stats import aggregate_recent_daily_stats
from app.jobs.workoutx_sync import sync_exercises

logger = get_logger(__name__)
scheduler = AsyncIOScheduler()


async def _run_sync() -> None:
    async with SessionLocal() as db:
        try:
            await sync_exercises(db)
        except Exception as exc:
            logger.exception("scheduled_sync_failed", error=str(exc))


async def _run_stats() -> None:
    async with SessionLocal() as db:
        try:
            await aggregate_recent_daily_stats(db)
        except Exception as exc:
            logger.exception("scheduled_stats_failed", error=str(exc))


def start_scheduler() -> None:
    if scheduler.running:
        return
    scheduler.add_job(_run_sync, "cron", hour=3, minute=0, id="workoutx_sync", replace_existing=True)
    scheduler.add_job(_run_stats, "cron", hour=3, minute=30, id="daily_stats", replace_existing=True)
    scheduler.start()
    logger.info("scheduler_started")


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)

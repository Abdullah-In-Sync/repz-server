from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.workout import WorkoutSession
from app.services.stats_service import recompute_daily_stats

logger = get_logger(__name__)


async def aggregate_recent_daily_stats(db: AsyncSession, days: int = 14) -> int:
    start = date.today() - timedelta(days=days)
    result = await db.execute(
        select(WorkoutSession.user_id, WorkoutSession.started_at).where(
            WorkoutSession.started_at >= start
        )
    )
    pairs = {(user_id, started_at.date()) for user_id, started_at in result.all()}
    for user_id, day in pairs:
        await recompute_daily_stats(db, user_id, day)
    await db.commit()
    logger.info("daily_stats_aggregated", pairs=len(pairs))
    return len(pairs)

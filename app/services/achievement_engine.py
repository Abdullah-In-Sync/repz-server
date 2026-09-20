from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.achievement import Achievement, AchievementType
from app.models.metrics import DailyStat

VOLUME_MILESTONES = [1_000, 10_000, 50_000, 100_000]


async def _has_achievement(
    db: AsyncSession, user_id: str, type_: AchievementType, dedupe_key: str
) -> bool:
    result = await db.execute(
        select(Achievement.id).where(
            Achievement.user_id == user_id,
            Achievement.type == type_,
            Achievement.dedupe_key == dedupe_key,
        )
    )
    return result.scalar_one_or_none() is not None


async def _unlock(
    db: AsyncSession,
    user_id: str,
    type_: AchievementType,
    dedupe_key: str,
    metadata: dict | None = None,
) -> None:
    if await _has_achievement(db, user_id, type_, dedupe_key):
        return
    db.add(
        Achievement(
            user_id=user_id,
            type=type_,
            dedupe_key=dedupe_key,
            metadata_json=metadata,
        )
    )


async def current_streak(db: AsyncSession, user_id: str) -> int:
    result = await db.execute(
        select(DailyStat.date)
        .where(DailyStat.user_id == user_id, DailyStat.total_sets > 0)
        .order_by(DailyStat.date.desc())
    )
    days = [row[0] for row in result.all()]
    if not days:
        return 0
    streak = 0
    expected = date.today()
    if days[0] < expected:
        expected = days[0]
    for day in days:
        if day == expected:
            streak += 1
            expected = expected - timedelta(days=1)
        elif day < expected:
            break
    return streak


async def evaluate_achievements(
    db: AsyncSession, user_id: str, prs_broken: list[dict] | None = None
) -> None:
    streak = await current_streak(db, user_id)
    if streak >= 7:
        await _unlock(db, user_id, AchievementType.STREAK_7, "default", {"streak": streak})
    if streak >= 30:
        await _unlock(db, user_id, AchievementType.STREAK_30, "default", {"streak": streak})

    if prs_broken:
        await _unlock(
            db,
            user_id,
            AchievementType.PR_BROKEN,
            "any",
            {"count": len(prs_broken)},
        )

    total_volume = float(
        (
            await db.execute(
                select(func.coalesce(func.sum(DailyStat.total_volume), 0)).where(
                    DailyStat.user_id == user_id
                )
            )
        ).scalar_one()
    )
    for milestone in VOLUME_MILESTONES:
        if total_volume >= milestone:
            await _unlock(
                db,
                user_id,
                AchievementType.VOLUME_MILESTONE,
                str(milestone),
                {"milestone": milestone, "total_volume": total_volume},
            )

    workout_days = int(
        (
            await db.execute(
                select(func.count()).select_from(DailyStat).where(
                    DailyStat.user_id == user_id, DailyStat.total_sets > 0
                )
            )
        ).scalar_one()
    )
    if workout_days >= 12:
        await _unlock(
            db,
            user_id,
            AchievementType.CONSISTENCY_BADGE,
            "12_days",
            {"workout_days": workout_days},
        )

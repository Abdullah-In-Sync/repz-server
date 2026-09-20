from datetime import date
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.exercise import Exercise
from app.models.metrics import DailyStat
from app.models.workout import WorkoutSession, WorkoutSet
from app.utils.training import set_volume


async def recompute_daily_stats(db: AsyncSession, user_id: str, day: date) -> DailyStat:
    sessions_result = await db.execute(
        select(WorkoutSession).where(
            WorkoutSession.user_id == user_id,
            func.date(WorkoutSession.started_at) == day,
        )
    )
    sessions = list(sessions_result.scalars().all())
    session_ids = [item.id for item in sessions]
    total_volume = 0.0
    total_sets = 0
    duration_seconds = sum(item.duration_seconds or 0 for item in sessions)
    calories_est = 0.0

    if session_ids:
        sets_result = await db.execute(
            select(WorkoutSet, Exercise)
            .join(Exercise, WorkoutSet.exercise_id == Exercise.id)
            .where(WorkoutSet.workout_session_id.in_(session_ids), WorkoutSet.is_completed.is_(True))
        )
        for workout_set, exercise in sets_result.all():
            total_sets += 1
            total_volume += set_volume(workout_set.weight_kg, workout_set.reps, workout_set.is_warmup)
            minutes = (workout_set.duration_seconds or 0) / 60.0
            if not minutes and workout_set.reps:
                minutes = workout_set.reps * 0.05
            if exercise.calories_per_minute:
                calories_est += float(exercise.calories_per_minute) * minutes

    result = await db.execute(
        select(DailyStat).where(DailyStat.user_id == user_id, DailyStat.date == day)
    )
    stat = result.scalar_one_or_none()
    if stat is None:
        stat = DailyStat(id=str(uuid4()), user_id=user_id, date=day)
        db.add(stat)
    stat.total_volume = total_volume
    stat.total_sets = total_sets
    stat.duration_seconds = duration_seconds
    stat.calories_est = round(calories_est, 2)
    await db.flush()
    return stat

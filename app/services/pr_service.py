from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.workout import PersonalRecord, RecordType, WorkoutSession
from app.utils.training import epley_1rm, set_volume


async def _upsert_pr(
    db: AsyncSession,
    user_id: str,
    exercise_id: str,
    record_type: RecordType,
    value: float,
    workout_set_id: str,
    achieved_at: datetime,
) -> bool:
    result = await db.execute(
        select(PersonalRecord).where(
            PersonalRecord.user_id == user_id,
            PersonalRecord.exercise_id == exercise_id,
            PersonalRecord.record_type == record_type,
        )
    )
    existing = result.scalar_one_or_none()
    if existing is None:
        db.add(
            PersonalRecord(
                user_id=user_id,
                exercise_id=exercise_id,
                record_type=record_type,
                value=value,
                workout_set_id=workout_set_id,
                achieved_at=achieved_at,
            )
        )
        return True
    if value > existing.value:
        existing.value = value
        existing.workout_set_id = workout_set_id
        existing.achieved_at = achieved_at
        return True
    return False


async def update_personal_records(
    db: AsyncSession, user: User, session: WorkoutSession
) -> list[dict]:
    broken: list[dict] = []
    for workout_set in session.sets:
        if not workout_set.is_completed or workout_set.is_warmup:
            continue
        candidates: list[tuple[RecordType, float]] = []
        if workout_set.weight_kg:
            candidates.append((RecordType.MAX_WEIGHT, float(workout_set.weight_kg)))
        if workout_set.reps:
            candidates.append((RecordType.MAX_REPS, float(workout_set.reps)))
        volume = set_volume(workout_set.weight_kg, workout_set.reps, False)
        if volume:
            candidates.append((RecordType.MAX_VOLUME, volume))
        if workout_set.weight_kg and workout_set.reps:
            candidates.append(
                (RecordType.BEST_1RM, epley_1rm(float(workout_set.weight_kg), int(workout_set.reps)))
            )
        if workout_set.duration_seconds:
            candidates.append((RecordType.LONGEST_DURATION, float(workout_set.duration_seconds)))
        if workout_set.distance_km:
            candidates.append((RecordType.LONGEST_DISTANCE, float(workout_set.distance_km)))

        for record_type, value in candidates:
            changed = await _upsert_pr(
                db,
                user.id,
                workout_set.exercise_id,
                record_type,
                value,
                workout_set.id,
                workout_set.created_at or datetime.utcnow(),
            )
            if changed:
                broken.append(
                    {
                        "exercise_id": workout_set.exercise_id,
                        "record_type": record_type.value,
                        "value": value,
                    }
                )
    return broken

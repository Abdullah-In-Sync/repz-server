from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.workout import PersonalRecord, RecordType, WorkoutSession, WorkoutSet
from app.utils.training import epley_1rm, set_volume


def _set_record_candidates(workout_set: WorkoutSet) -> list[tuple[RecordType, float]]:
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
    return candidates


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
        for record_type, value in _set_record_candidates(workout_set):
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


async def clear_pr_links_for_sets(db: AsyncSession, set_ids: list[str]) -> None:
    if not set_ids:
        return
    result = await db.execute(
        select(PersonalRecord).where(PersonalRecord.workout_set_id.in_(set_ids))
    )
    for pr in result.scalars():
        pr.workout_set_id = None
    await db.flush()


async def rebuild_personal_records_for_exercises(
    db: AsyncSession, user_id: str, exercise_ids: set[str]
) -> None:
    if not exercise_ids:
        return
    await db.execute(
        delete(PersonalRecord).where(
            PersonalRecord.user_id == user_id,
            PersonalRecord.exercise_id.in_(exercise_ids),
        )
    )
    result = await db.execute(
        select(WorkoutSet, WorkoutSession)
        .join(WorkoutSession, WorkoutSet.workout_session_id == WorkoutSession.id)
        .where(
            WorkoutSession.user_id == user_id,
            WorkoutSet.exercise_id.in_(exercise_ids),
            WorkoutSet.is_completed.is_(True),
            WorkoutSet.is_warmup.is_(False),
        )
    )
    bests: dict[tuple[str, RecordType], tuple[float, str, datetime]] = {}
    for workout_set, _session in result.all():
        achieved_at = workout_set.created_at or datetime.utcnow()
        for record_type, value in _set_record_candidates(workout_set):
            key = (workout_set.exercise_id, record_type)
            prev = bests.get(key)
            if prev is None or value > prev[0]:
                bests[key] = (value, workout_set.id, achieved_at)
    for (exercise_id, record_type), (value, set_id, achieved_at) in bests.items():
        db.add(
            PersonalRecord(
                user_id=user_id,
                exercise_id=exercise_id,
                record_type=record_type,
                value=value,
                workout_set_id=set_id,
                achieved_at=achieved_at,
            )
        )
    await db.flush()

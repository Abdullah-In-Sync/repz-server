from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.exercise import Exercise
from app.models.routine import Routine
from app.models.user import User
from app.models.workout import WorkoutSession, WorkoutSet
from app.schemas.workout import SetCreate, SetUpdate, WorkoutCreate, WorkoutUpdate
from app.services.achievement_engine import evaluate_achievements
from app.services.pr_service import update_personal_records
from app.services.stats_service import recompute_daily_stats
from app.utils.training import set_volume


class WorkoutValidationError(ValueError):
    pass


async def _load_session(db: AsyncSession, user: User, workout_id: str) -> WorkoutSession | None:
    result = await db.execute(
        select(WorkoutSession)
        .options(selectinload(WorkoutSession.sets))
        .where(WorkoutSession.id == workout_id, WorkoutSession.user_id == user.id)
    )
    return result.scalar_one_or_none()


def compute_session_volume(session: WorkoutSession) -> float:
    return sum(
        set_volume(item.weight_kg, item.reps, item.is_warmup)
        for item in session.sets
        if item.is_completed
    )


async def refresh_session_side_effects(db: AsyncSession, user: User, session: WorkoutSession) -> None:
    await db.refresh(session, attribute_names=["sets"])
    session.total_volume_kg = compute_session_volume(session)
    await db.flush()
    broken = await update_personal_records(db, user, session)
    await recompute_daily_stats(db, user.id, session.started_at.date())
    await evaluate_achievements(db, user.id, prs_broken=broken)
    await db.commit()
    await db.refresh(session)


async def create_workout(db: AsyncSession, user: User, payload: WorkoutCreate) -> WorkoutSession:
    if payload.routine_id:
        routine = await db.get(Routine, payload.routine_id)
        if not routine or routine.user_id != user.id:
            raise WorkoutValidationError("Routine not found")
        routine.last_used_at = datetime.now(UTC).replace(tzinfo=None)
    session = WorkoutSession(
        user_id=user.id,
        routine_id=payload.routine_id,
        name=payload.name,
        notes=payload.notes,
        body_weight_kg=payload.body_weight_kg,
        started_at=payload.started_at or datetime.utcnow(),
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


async def list_workouts(
    db: AsyncSession,
    user: User,
    *,
    limit: int,
    offset: int,
    start: datetime | None,
    end: datetime | None,
) -> tuple[list[WorkoutSession], int]:
    from sqlalchemy import func

    filters = [WorkoutSession.user_id == user.id]
    if start:
        filters.append(WorkoutSession.started_at >= start)
    if end:
        filters.append(WorkoutSession.started_at <= end)
    total = int(
        (await db.execute(select(func.count()).select_from(WorkoutSession).where(*filters))).scalar_one()
    )
    result = await db.execute(
        select(WorkoutSession)
        .options(selectinload(WorkoutSession.sets))
        .where(*filters)
        .order_by(WorkoutSession.started_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all()), total


async def get_workout(db: AsyncSession, user: User, workout_id: str) -> WorkoutSession | None:
    return await _load_session(db, user, workout_id)


async def update_workout(
    db: AsyncSession, user: User, session: WorkoutSession, payload: WorkoutUpdate
) -> WorkoutSession:
    data = payload.model_dump(exclude_unset=True, exclude={"finish"})
    for key, value in data.items():
        setattr(session, key, value)
    if payload.finish and not session.ended_at:
        session.ended_at = datetime.utcnow()
    if session.ended_at and session.started_at and session.duration_seconds is None:
        session.duration_seconds = int((session.ended_at - session.started_at).total_seconds())
    await refresh_session_side_effects(db, user, session)
    return session


async def _validate_set_fields(exercise: Exercise, payload: SetCreate | SetUpdate) -> None:
    if isinstance(payload, SetCreate):
        if exercise.is_time_based and payload.duration_seconds is None and payload.reps is None:
            raise WorkoutValidationError("Time-based exercises require duration_seconds or reps")
        if exercise.is_distance_based and payload.distance_km is None and payload.reps is None:
            raise WorkoutValidationError("Distance-based exercises require distance_km or reps")
        if not exercise.is_time_based and payload.duration_seconds:
            raise WorkoutValidationError("duration_seconds is only valid for time-based exercises")
        if not exercise.is_distance_based and payload.distance_km:
            raise WorkoutValidationError("distance_km is only valid for distance-based exercises")


async def add_set(
    db: AsyncSession, user: User, session: WorkoutSession, payload: SetCreate
) -> WorkoutSet:
    exercise = await db.get(Exercise, payload.exercise_id)
    if not exercise:
        raise WorkoutValidationError("Exercise not found")
    await _validate_set_fields(exercise, payload)
    workout_set = WorkoutSet(workout_session_id=session.id, **payload.model_dump())
    db.add(workout_set)
    await db.flush()
    await refresh_session_side_effects(db, user, session)
    await db.refresh(workout_set)
    return workout_set


async def update_set(
    db: AsyncSession,
    user: User,
    session: WorkoutSession,
    set_id: str,
    payload: SetUpdate,
) -> WorkoutSet:
    workout_set = next((item for item in session.sets if item.id == set_id), None)
    if not workout_set:
        raise WorkoutValidationError("Set not found")
    exercise = await db.get(Exercise, workout_set.exercise_id)
    if exercise:
        await _validate_set_fields(exercise, payload)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(workout_set, key, value)
    await refresh_session_side_effects(db, user, session)
    await db.refresh(workout_set)
    return workout_set


async def delete_set(db: AsyncSession, user: User, session: WorkoutSession, set_id: str) -> None:
    workout_set = next((item for item in session.sets if item.id == set_id), None)
    if not workout_set:
        raise WorkoutValidationError("Set not found")
    await db.delete(workout_set)
    await db.flush()
    await refresh_session_side_effects(db, user, session)

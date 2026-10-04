from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.exercise import Exercise
from app.models.routine import Routine, RoutineExercise
from app.models.user import User
from app.models.workout import WorkoutSession, WorkoutSet
from app.schemas.routine import RoutineCreate, RoutineUpdate


async def list_routines(db: AsyncSession, user: User) -> list[Routine]:
    result = await db.execute(
        select(Routine)
        .options(selectinload(Routine.exercises).selectinload(RoutineExercise.exercise))
        .where(Routine.user_id == user.id)
        .order_by(Routine.updated_at.desc())
    )
    return list(result.scalars().all())


async def get_routine(db: AsyncSession, user: User, routine_id: str) -> Routine | None:
    result = await db.execute(
        select(Routine)
        .options(selectinload(Routine.exercises).selectinload(RoutineExercise.exercise))
        .where(Routine.id == routine_id, Routine.user_id == user.id)
    )
    return result.scalar_one_or_none()


async def _replace_exercises(db: AsyncSession, routine: Routine, items) -> None:
    """Replace all routine_exercises rows without touching the ORM relationship.

    Touching `routine.exercises` (via .clear() or .append()) triggers a lazy load
    in async context, which raises MissingGreenlet. So we do direct SQL instead.
    """
    # Delete existing rows for this routine
    await db.execute(
        delete(RoutineExercise).where(RoutineExercise.routine_id == routine.id)
    )

    # Insert new rows
    for item in items:
        exercise = await db.get(Exercise, item.exercise_id)
        if not exercise:
            raise ValueError(f"Unknown exercise {item.exercise_id}")
        db.add(
            RoutineExercise(
                routine_id=routine.id,
                exercise_id=item.exercise_id,
                order_index=item.order_index,
                target_sets=item.target_sets,
                target_reps_range=item.target_reps_range,
                target_duration_seconds=item.target_duration_seconds,
                target_distance_km=item.target_distance_km,
                target_weight_kg=item.target_weight_kg,
                rest_seconds=item.rest_seconds,
                notes=item.notes,
                set_targets=(
                    [target.model_dump() for target in item.set_targets]
                    if item.set_targets is not None
                    else None
                ),
            )
        )

    await db.flush()


async def create_routine(db: AsyncSession, user: User, payload: RoutineCreate) -> Routine:
    routine = Routine(
        user_id=user.id,
        name=payload.name,
        description=payload.description,
        folder=payload.folder,
    )
    db.add(routine)
    await db.flush()
    await _replace_exercises(db, routine, payload.exercises)
    await db.commit()
    return await get_routine(db, user, routine.id)  # type: ignore[return-value]


async def update_routine(
    db: AsyncSession, user: User, routine: Routine, payload: RoutineUpdate
) -> Routine:
    data = payload.model_dump(exclude_unset=True, exclude={"exercises"})
    for key, value in data.items():
        setattr(routine, key, value)
    if payload.exercises is not None:
        await _replace_exercises(db, routine, payload.exercises)
    routine.updated_at = datetime.utcnow()
    await db.commit()
    return await get_routine(db, user, routine.id)  # type: ignore[return-value]


async def delete_routine(db: AsyncSession, routine: Routine) -> None:
    await db.delete(routine)
    await db.commit()


async def last_logged(db: AsyncSession, user: User, routine: Routine) -> list[dict]:
    name_by_id = {
        item.exercise_id: (item.exercise.name if item.exercise else item.exercise_id)
        for item in routine.exercises
    }
    session_result = await db.execute(
        select(WorkoutSession)
        .where(
            WorkoutSession.user_id == user.id,
            WorkoutSession.routine_id == routine.id,
            WorkoutSession.ended_at.isnot(None),
        )
        .order_by(WorkoutSession.ended_at.desc())
        .limit(1)
    )
    last_session = session_result.scalar_one_or_none()
    if not last_session:
        return []

    sets_result = await db.execute(
        select(WorkoutSet)
        .where(
            WorkoutSet.workout_session_id == last_session.id,
            WorkoutSet.is_completed.is_(True),
        )
        .order_by(WorkoutSet.exercise_id, WorkoutSet.set_number)
    )
    rows = []
    for logged in sets_result.scalars().all():
        rows.append(
            {
                "exercise_id": logged.exercise_id,
                "exercise_name": name_by_id.get(logged.exercise_id, logged.exercise_id),
                "set_number": logged.set_number,
                "weight_kg": logged.weight_kg,
                "reps": logged.reps,
                "rpe": logged.rpe,
                "duration_seconds": logged.duration_seconds,
                "distance_km": logged.distance_km,
                "logged_at": logged.created_at,
            }
        )
    return rows
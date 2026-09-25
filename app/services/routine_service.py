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
                rest_seconds=item.rest_seconds,
                notes=item.notes,
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
    rows = []
    for item in routine.exercises:
        result = await db.execute(
            select(WorkoutSet)
            .join(WorkoutSession, WorkoutSet.workout_session_id == WorkoutSession.id)
            .where(
                WorkoutSet.exercise_id == item.exercise_id,
                WorkoutSet.is_completed.is_(True),
                WorkoutSession.user_id == user.id,
            )
            .order_by(WorkoutSet.created_at.desc())
            .limit(1)
        )
        logged = result.scalar_one_or_none()
        rows.append(
            {
                "exercise_id": item.exercise_id,
                "exercise_name": item.exercise.name if item.exercise else None,
                "weight_kg": logged.weight_kg if logged else None,
                "reps": logged.reps if logged else None,
                "rpe": logged.rpe if logged else None,
                "duration_seconds": logged.duration_seconds if logged else None,
                "distance_km": logged.distance_km if logged else None,
                "logged_at": logged.created_at if logged else None,
            }
        )
    return rows
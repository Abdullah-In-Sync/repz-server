from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import cache_delete
from app.models.exercise import Exercise, ExerciseSource
from app.models.user import User
from app.schemas.exercise import ExerciseCreateCustom, ExerciseUpdate


async def list_exercises(
    db: AsyncSession,
    user: User,
    *,
    body_part: str | None,
    target: str | None,
    equipment: str | None,
    search: str | None,
    limit: int,
    offset: int,
) -> tuple[list[Exercise], int]:
    filters = [
        or_(
            Exercise.source == ExerciseSource.CATALOG,
            Exercise.created_by_user_id == user.id,
        )
    ]
    if body_part:
        filters.append(Exercise.body_part == body_part)
    if target:
        filters.append(Exercise.target == target)
    if equipment:
        filters.append(Exercise.equipment == equipment)
    if search:
        filters.append(Exercise.name.ilike(f"%{search}%"))

    count_q = select(func.count()).select_from(Exercise).where(*filters)
    total = int((await db.execute(count_q)).scalar_one())
    result = await db.execute(
        select(Exercise).where(*filters).order_by(Exercise.name.asc()).limit(limit).offset(offset)
    )
    return list(result.scalars().all()), total


async def get_exercise(db: AsyncSession, user: User, exercise_id: str) -> Exercise | None:
    result = await db.execute(select(Exercise).where(Exercise.id == exercise_id))
    exercise = result.scalar_one_or_none()
    if not exercise:
        return None
    if exercise.source == ExerciseSource.CUSTOM and exercise.created_by_user_id != user.id:
        return None
    return exercise


def _can_mutate(user: User, exercise: Exercise) -> bool:
    if exercise.source == ExerciseSource.CATALOG:
        return True
    return exercise.created_by_user_id == user.id


async def create_custom_exercise(
    db: AsyncSession, user: User, payload: ExerciseCreateCustom
) -> Exercise:
    exercise = Exercise(
        source=ExerciseSource.CUSTOM,
        created_by_user_id=user.id,
        **payload.model_dump(),
    )
    db.add(exercise)
    await db.commit()
    await db.refresh(exercise)
    await cache_delete("exercises:filters")
    return exercise


async def update_exercise(
    db: AsyncSession, user: User, exercise: Exercise, payload: ExerciseUpdate
) -> Exercise:
    if not _can_mutate(user, exercise):
        raise PermissionError("Not allowed to edit this exercise")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(exercise, key, value)
    await db.commit()
    await db.refresh(exercise)
    await cache_delete("exercises:filters")
    return exercise


async def delete_exercise(db: AsyncSession, user: User, exercise: Exercise) -> None:
    if not _can_mutate(user, exercise):
        raise PermissionError("Not allowed to delete this exercise")
    try:
        db.delete(exercise)
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise ValueError("Exercise is referenced by routines or workouts") from exc
    await cache_delete("exercises:filters")


async def distinct_filters(db: AsyncSession) -> dict[str, list[str]]:
    async def _col(column) -> list[str]:
        rows = await db.execute(
            select(column).where(column.is_not(None)).distinct().order_by(column.asc())
        )
        return [row[0] for row in rows.all() if row[0]]

    return {
        "body_parts": await _col(Exercise.body_part),
        "targets": await _col(Exercise.target),
        "equipment": await _col(Exercise.equipment),
    }

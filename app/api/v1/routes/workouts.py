from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, status

from app.api.v1.deps import CurrentUser, DbDep, PaginationDep
from app.core.logging import get_logger
from app.schemas.common import PaginatedResponse
from app.schemas.workout import SetCreate, SetRead, SetUpdate, WorkoutCreate, WorkoutRead, WorkoutUpdate
from app.services.workout_service import (
    WorkoutValidationError,
    add_set,
    create_workout,
    delete_set,
    get_workout,
    list_workouts,
    update_set,
    update_workout,
)

router = APIRouter(prefix="/workouts", tags=["workouts"])
logger = get_logger(__name__)


@router.post("", response_model=WorkoutRead, status_code=status.HTTP_201_CREATED)
async def start_workout(payload: WorkoutCreate, db: DbDep, user: CurrentUser):
    try:
        session = await create_workout(db, user, payload)
    except WorkoutValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return session


@router.get("", response_model=PaginatedResponse[WorkoutRead])
async def history(
    db: DbDep,
    user: CurrentUser,
    pagination: PaginationDep,
    start: datetime | None = Query(default=None),
    end: datetime | None = Query(default=None),
):
    limit, offset = pagination
    items, total = await list_workouts(db, user, limit=limit, offset=offset, start=start, end=end)
    return PaginatedResponse[WorkoutRead](items=items, total=total, limit=limit, offset=offset)


@router.get("/{workout_id}", response_model=WorkoutRead)
async def get_one(workout_id: str, db: DbDep, user: CurrentUser):
    session = await get_workout(db, user, workout_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workout not found")
    return session


@router.patch("/{workout_id}", response_model=WorkoutRead)
async def patch_workout(
    workout_id: str, payload: WorkoutUpdate, db: DbDep, user: CurrentUser
):
    session = await get_workout(db, user, workout_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workout not found")
    return await update_workout(db, user, session, payload)


@router.post("/{workout_id}/sets", response_model=SetRead, status_code=status.HTTP_201_CREATED)
async def log_set(
    workout_id: str, payload: SetCreate, db: DbDep, user: CurrentUser
):
    session = await get_workout(db, user, workout_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workout not found")
    try:
        return await add_set(db, user, session, payload)
    except WorkoutValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.patch("/{workout_id}/sets/{set_id}", response_model=SetRead)
async def patch_set(
    workout_id: str, set_id: str, payload: SetUpdate, db: DbDep, user: CurrentUser
):
    session = await get_workout(db, user, workout_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workout not found")
    try:
        return await update_set(db, user, session, set_id, payload)
    except WorkoutValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.delete("/{workout_id}/sets/{set_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_set(workout_id: str, set_id: str, db: DbDep, user: CurrentUser) -> None:
    session = await get_workout(db, user, workout_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workout not found")
    logger.info("set_deleted", workout_id=workout_id, set_id=set_id, user_id=user.id)
    try:
        await delete_set(db, user, session, set_id)
    except WorkoutValidationError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

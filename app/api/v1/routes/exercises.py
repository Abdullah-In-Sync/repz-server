from fastapi import APIRouter, HTTPException, Query, status

from app.api.v1.deps import CurrentUser, DbDep, PaginationDep
from app.core.redis import json_cache_get, json_cache_set
from app.schemas.common import PaginatedResponse
from app.schemas.exercise import ExerciseCreateCustom, ExerciseFilters, ExerciseRead
from app.services import exercise_service

router = APIRouter(prefix="/exercises", tags=["exercises"])


@router.get("", response_model=PaginatedResponse[ExerciseRead])
async def list_exercises(
    db: DbDep,
    user: CurrentUser,
    pagination: PaginationDep,
    body_part: str | None = Query(default=None, alias="bodyPart"),
    target: str | None = None,
    equipment: str | None = None,
    search: str | None = None,
):
    limit, offset = pagination
    items, total = await exercise_service.list_exercises(
        db,
        user,
        body_part=body_part,
        target=target,
        equipment=equipment,
        search=search,
        limit=limit,
        offset=offset,
    )
    return PaginatedResponse[ExerciseRead](
        items=items, total=total, limit=limit, offset=offset
    )


@router.get("/filters", response_model=ExerciseFilters)
async def filters(db: DbDep, user: CurrentUser) -> ExerciseFilters:
    cached = await json_cache_get("exercises:filters")
    if cached:
        try:
            return ExerciseFilters(**cached)
        except Exception:
            pass
    data = await exercise_service.distinct_filters(db)
    await json_cache_set("exercises:filters", data, 60 * 60 * 24)
    return ExerciseFilters(**data)


@router.post("/custom", response_model=ExerciseRead, status_code=status.HTTP_201_CREATED)
async def create_custom(
    payload: ExerciseCreateCustom, db: DbDep, user: CurrentUser
):
    return await exercise_service.create_custom_exercise(db, user, payload)


@router.get("/{exercise_id}", response_model=ExerciseRead)
async def get_exercise(exercise_id: str, db: DbDep, user: CurrentUser):
    exercise = await exercise_service.get_exercise(db, user, exercise_id)
    if not exercise:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exercise not found")
    return exercise

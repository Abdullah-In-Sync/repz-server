from fastapi import APIRouter, File, HTTPException, Query, UploadFile, status

from app.api.v1.deps import CurrentUser, DbDep, PaginationDep
from app.core.redis import cache_delete, json_cache_get, json_cache_set
from app.schemas.common import PaginatedResponse
from app.schemas.exercise import ExerciseCreateCustom, ExerciseFilters, ExerciseRead, ExerciseUpdate
from app.services import exercise_service
from app.utils.media import media_key_for_exercise, save_gif_and_thumb

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


@router.patch("/{exercise_id}", response_model=ExerciseRead)
async def patch_exercise(
    exercise_id: str, payload: ExerciseUpdate, db: DbDep, user: CurrentUser
):
    exercise = await exercise_service.get_exercise(db, user, exercise_id)
    if not exercise:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exercise not found")
    try:
        return await exercise_service.update_exercise(db, user, exercise, payload)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.delete("/{exercise_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_exercise(exercise_id: str, db: DbDep, user: CurrentUser):
    exercise = await exercise_service.get_exercise(db, user, exercise_id)
    if not exercise:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exercise not found")
    try:
        await exercise_service.delete_exercise(db, user, exercise)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.post("/{exercise_id}/gif", response_model=ExerciseRead)
async def upload_exercise_gif(
    exercise_id: str,
    db: DbDep,
    user: CurrentUser,
    file: UploadFile = File(...),
):
    exercise = await exercise_service.get_exercise(db, user, exercise_id)
    if not exercise:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exercise not found")
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Image file required")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file")

    key = media_key_for_exercise(exercise)
    if not key:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing media key")
    gif_url = save_gif_and_thumb(key, content)
    exercise.gif_url = gif_url
    await db.commit()
    await db.refresh(exercise)
    await cache_delete("exercises:filters")
    return exercise

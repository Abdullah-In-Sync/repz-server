from fastapi import APIRouter, HTTPException, status

from app.api.v1.deps import CurrentUser, DbDep
from app.core.logging import get_logger
from app.schemas.routine import LastLoggedSet, RoutineCreate, RoutineExerciseRead, RoutineRead, RoutineUpdate
from app.services import routine_service

router = APIRouter(prefix="/routines", tags=["routines"])
logger = get_logger(__name__)


def _to_read(routine) -> RoutineRead:
    return RoutineRead(
        id=routine.id,
        user_id=routine.user_id,
        name=routine.name,
        description=routine.description,
        folder=routine.folder,
        created_at=routine.created_at,
        updated_at=routine.updated_at,
        last_used_at=routine.last_used_at,
        exercises=[
            RoutineExerciseRead(
                id=item.id,
                exercise_id=item.exercise_id,
                order_index=item.order_index,
                target_sets=item.target_sets,
                target_reps_range=item.target_reps_range,
                rest_seconds=item.rest_seconds,
                notes=item.notes,
                exercise_name=item.exercise.name if item.exercise else None,
            )
            for item in routine.exercises
        ],
    )


@router.get("", response_model=list[RoutineRead])
async def list_routines(db: DbDep, user: CurrentUser) -> list[RoutineRead]:
    routines = await routine_service.list_routines(db, user)
    return [_to_read(item) for item in routines]


@router.post("", response_model=RoutineRead, status_code=status.HTTP_201_CREATED)
async def create_routine(payload: RoutineCreate, db: DbDep, user: CurrentUser) -> RoutineRead:
    try:
        routine = await routine_service.create_routine(db, user, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _to_read(routine)


@router.get("/{routine_id}", response_model=RoutineRead)
async def get_routine(routine_id: str, db: DbDep, user: CurrentUser) -> RoutineRead:
    routine = await routine_service.get_routine(db, user, routine_id)
    if not routine:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Routine not found")
    return _to_read(routine)


@router.patch("/{routine_id}", response_model=RoutineRead)
async def update_routine(
    routine_id: str, payload: RoutineUpdate, db: DbDep, user: CurrentUser
) -> RoutineRead:
    routine = await routine_service.get_routine(db, user, routine_id)
    if not routine:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Routine not found")
    try:
        routine = await routine_service.update_routine(db, user, routine, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _to_read(routine)


@router.delete("/{routine_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_routine(routine_id: str, db: DbDep, user: CurrentUser) -> None:
    routine = await routine_service.get_routine(db, user, routine_id)
    if not routine:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Routine not found")
    logger.info("routine_deleted", routine_id=routine_id, user_id=user.id)
    await routine_service.delete_routine(db, routine)


@router.get("/{routine_id}/last-logged", response_model=list[LastLoggedSet])
async def last_logged(routine_id: str, db: DbDep, user: CurrentUser) -> list[LastLoggedSet]:
    routine = await routine_service.get_routine(db, user, routine_id)
    if not routine:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Routine not found")
    rows = await routine_service.last_logged(db, user, routine)
    return [LastLoggedSet(**row) for row in rows]

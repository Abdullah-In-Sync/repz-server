from fastapi import APIRouter

from app.api.v1.deps import CurrentUser, DbDep
from app.schemas.user import UserRead, UserSyncRequest, UserUpdate
from app.services import user_service

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/sync", response_model=UserRead)
async def sync_user(payload: UserSyncRequest, db: DbDep, user: CurrentUser):
    return await user_service.sync_user(db, user, payload)


@router.get("/me", response_model=UserRead)
async def me(user: CurrentUser):
    return user


@router.patch("/me", response_model=UserRead)
async def update_me(payload: UserUpdate, db: DbDep, user: CurrentUser):
    return await user_service.update_user(db, user, payload)

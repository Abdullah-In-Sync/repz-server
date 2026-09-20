from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.schemas.user import UserSyncRequest, UserUpdate


async def get_or_create_user(
    db: AsyncSession,
    firebase_uid: str,
    email: str | None = None,
    display_name: str | None = None,
    avatar_url: str | None = None,
) -> User:
    result = await db.execute(select(User).where(User.firebase_uid == firebase_uid))
    user = result.scalar_one_or_none()
    if user:
        changed = False
        if email and user.email != email:
            user.email = email
            changed = True
        if display_name and not user.display_name:
            user.display_name = display_name
            changed = True
        if avatar_url and not user.avatar_url:
            user.avatar_url = avatar_url
            changed = True
        if changed:
            user.updated_at = datetime.utcnow()
            await db.commit()
            await db.refresh(user)
        return user

    user = User(
        firebase_uid=firebase_uid,
        email=email,
        display_name=display_name,
        avatar_url=avatar_url,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def sync_user(db: AsyncSession, user: User, payload: UserSyncRequest) -> User:
    if payload.display_name is not None:
        user.display_name = payload.display_name
    if payload.avatar_url is not None:
        user.avatar_url = payload.avatar_url
    if payload.timezone is not None:
        user.timezone = payload.timezone
    user.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(user)
    return user


async def update_user(db: AsyncSession, user: User, payload: UserUpdate) -> User:
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(user, key, value)
    user.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(user)
    return user

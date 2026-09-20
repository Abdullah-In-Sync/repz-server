from datetime import date, datetime

from pydantic import BaseModel, Field

from app.models.user import Gender, UnitPreference


class UserSyncRequest(BaseModel):
    display_name: str | None = None
    avatar_url: str | None = None
    timezone: str | None = None


class UserUpdate(BaseModel):
    display_name: str | None = None
    avatar_url: str | None = None
    unit_preference: UnitPreference | None = None
    timezone: str | None = None
    height_cm: float | None = Field(default=None, ge=50, le=300)
    date_of_birth: date | None = None
    gender: Gender | None = None


class UserRead(BaseModel):
    id: str
    firebase_uid: str
    email: str | None
    display_name: str | None
    avatar_url: str | None
    unit_preference: UnitPreference
    timezone: str
    height_cm: float | None
    date_of_birth: date | None
    gender: Gender | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

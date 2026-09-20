from datetime import date, datetime

from pydantic import BaseModel

from app.models.achievement import AchievementType
from app.models.workout import RecordType


class DailyReport(BaseModel):
    date: date
    total_volume: float
    total_sets: int
    duration_seconds: int
    calories_est: float
    workout_count: int = 0


class RangeReport(BaseModel):
    start: date
    end: date
    total_volume: float
    total_sets: int
    duration_seconds: int
    calories_est: float
    workout_days: int
    daily: list[DailyReport]


class CalendarDay(BaseModel):
    date: date
    has_workout: bool
    total_volume: float = 0


class VolumePoint(BaseModel):
    date: date
    volume: float


class MuscleShare(BaseModel):
    body_part: str
    volume: float
    percent: float


class AchievementRead(BaseModel):
    id: str
    type: AchievementType
    metadata: dict | None = None
    unlocked_at: datetime

    model_config = {"from_attributes": True}


class PersonalRecordRead(BaseModel):
    id: str
    exercise_id: str
    exercise_name: str | None = None
    record_type: RecordType
    value: float
    achieved_at: datetime

    model_config = {"from_attributes": True}

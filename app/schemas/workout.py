from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class WorkoutCreate(BaseModel):
    name: str | None = None
    routine_id: str | None = None
    notes: str | None = None
    body_weight_kg: float | None = Field(default=None, ge=20, le=400)
    started_at: datetime | None = None


class WorkoutUpdate(BaseModel):
    name: str | None = None
    notes: str | None = None
    body_weight_kg: float | None = Field(default=None, ge=20, le=400)
    ended_at: datetime | None = None
    duration_seconds: int | None = Field(default=None, ge=0)
    finish: bool = False


class SetCreate(BaseModel):
    exercise_id: str
    set_number: int = Field(default=1, ge=1, le=100)
    weight_kg: float | None = Field(default=None, ge=0, le=1000)
    reps: int | None = Field(default=None, ge=0, le=1000)
    rpe: float | None = None
    duration_seconds: int | None = Field(default=None, ge=0)
    distance_km: float | None = Field(default=None, ge=0)
    is_warmup: bool = False
    is_completed: bool = True

    @field_validator("rpe")
    @classmethod
    def validate_rpe(cls, value: float | None) -> float | None:
        if value is None:
            return value
        if value < 1 or value > 10:
            raise ValueError("RPE must be between 1 and 10")
        if (value * 2) % 1 != 0:
            raise ValueError("RPE must be in 0.5 steps")
        return value


class SetUpdate(BaseModel):
    set_number: int | None = Field(default=None, ge=1, le=100)
    weight_kg: float | None = Field(default=None, ge=0, le=1000)
    reps: int | None = Field(default=None, ge=0, le=1000)
    rpe: float | None = None
    duration_seconds: int | None = Field(default=None, ge=0)
    distance_km: float | None = Field(default=None, ge=0)
    is_warmup: bool | None = None
    is_completed: bool | None = None

    @field_validator("rpe")
    @classmethod
    def validate_rpe(cls, value: float | None) -> float | None:
        return SetCreate.validate_rpe(value)


class SetRead(BaseModel):
    id: str
    workout_session_id: str
    exercise_id: str
    set_number: int
    weight_kg: float | None
    reps: int | None
    rpe: float | None
    duration_seconds: int | None
    distance_km: float | None
    is_warmup: bool
    is_completed: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class WorkoutRead(BaseModel):
    id: str
    user_id: str
    routine_id: str | None
    name: str | None
    started_at: datetime
    ended_at: datetime | None
    duration_seconds: int | None
    notes: str | None
    body_weight_kg: float | None
    total_volume_kg: float
    created_at: datetime
    sets: list[SetRead] = Field(default_factory=list)

    model_config = {"from_attributes": True}

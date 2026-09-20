from datetime import datetime

from pydantic import BaseModel, Field


class RoutineExerciseIn(BaseModel):
    exercise_id: str
    order_index: int = 0
    target_sets: int | None = Field(default=None, ge=1, le=50)
    target_reps_range: str | None = None
    rest_seconds: int | None = Field(default=None, ge=0, le=600)
    notes: str | None = None


class RoutineExerciseRead(RoutineExerciseIn):
    id: str
    exercise_name: str | None = None

    model_config = {"from_attributes": True}


class RoutineCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    folder: str | None = None
    exercises: list[RoutineExerciseIn] = Field(default_factory=list)


class RoutineUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    folder: str | None = None
    exercises: list[RoutineExerciseIn] | None = None


class RoutineRead(BaseModel):
    id: str
    user_id: str
    name: str
    description: str | None
    folder: str | None
    created_at: datetime
    updated_at: datetime
    last_used_at: datetime | None
    exercises: list[RoutineExerciseRead] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class LastLoggedSet(BaseModel):
    exercise_id: str
    exercise_name: str
    weight_kg: float | None
    reps: int | None
    rpe: float | None
    duration_seconds: int | None
    distance_km: float | None
    logged_at: datetime | None

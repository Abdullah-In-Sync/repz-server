from datetime import datetime

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.exercise import ExerciseSource
from app.utils.media import is_legacy_remote_gif, public_gif_url, resolve_local_gif


def as_str_list(value) -> list | None:
    if value is None:
        return None
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        return [value] if value else None
    if isinstance(value, dict):
        items = [str(item) for item in value.values() if item is not None]
        return items or None
    return None


class ExerciseCreateCustom(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    body_part: str | None = None
    target: str | None = None
    equipment: str | None = None
    secondary_muscles: list[str] | None = None
    instructions: list[str] | None = None
    category: str | None = None
    difficulty: str | None = None
    mechanic: str | None = None
    force: str | None = None
    is_unilateral: bool = False
    is_time_based: bool = False
    is_distance_based: bool = False
    is_load_based: bool = False
    is_reps_based: bool = True
    description: str | None = None
    recommended_sets: str | None = None
    recommended_reps: str | None = None


class ExerciseUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    body_part: str | None = None
    target: str | None = None
    equipment: str | None = None
    secondary_muscles: list[str] | None = None
    instructions: list[str] | None = None
    category: str | None = None
    difficulty: str | None = None
    mechanic: str | None = None
    force: str | None = None
    is_unilateral: bool | None = None
    is_time_based: bool | None = None
    is_distance_based: bool | None = None
    is_load_based: bool | None = None
    is_reps_based: bool | None = None
    description: str | None = None
    recommended_sets: str | None = None
    recommended_reps: str | None = None
    gif_url: str | None = Field(default=None, max_length=1024)


class ExerciseRead(BaseModel):
    id: str
    source: ExerciseSource
    external_id: str | None
    name: str
    body_part: str | None
    target: str | None
    equipment: str | None
    secondary_muscles: list | None
    instructions: list | None
    gif_url: str | None
    category: str | None
    difficulty: str | None
    mechanic: str | None
    force: str | None
    met: float | None
    calories_per_minute: float | None
    is_unilateral: bool
    recommended_sets: str | None
    recommended_reps: str | None
    movement_tags: list | None
    created_by_user_id: str | None
    is_time_based: bool
    is_distance_based: bool
    is_load_based: bool
    is_reps_based: bool
    description: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @field_validator("secondary_muscles", "instructions", "movement_tags", mode="before")
    @classmethod
    def coerce_optional_lists(cls, value):
        return as_str_list(value)

    @model_validator(mode="after")
    def resolve_gif_url(self):
        for key in (self.external_id, self.id):
            if key and resolve_local_gif(str(key)):
                self.gif_url = public_gif_url(str(key))
                return self
        if is_legacy_remote_gif(self.gif_url):
            self.gif_url = None
        return self


class ExerciseFilters(BaseModel):
    body_parts: list[str]
    targets: list[str]
    equipment: list[str]

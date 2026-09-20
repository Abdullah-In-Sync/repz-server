from datetime import date, datetime

from pydantic import BaseModel, Field


class BodyMetricCreate(BaseModel):
    date: date
    weight_kg: float = Field(ge=20, le=400)
    body_fat_pct: float | None = Field(default=None, ge=1, le=70)
    notes: str | None = None


class BodyMetricRead(BaseModel):
    id: str
    user_id: str
    date: date
    weight_kg: float
    body_fat_pct: float | None
    notes: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class GraphPoint(BaseModel):
    date: date
    value: float

from typing import Any

from pydantic import BaseModel, Field


class PaginationParams(BaseModel):
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class PaginatedResponse[T](BaseModel):
    items: list[T] | list[Any]
    total: int
    limit: int
    offset: int

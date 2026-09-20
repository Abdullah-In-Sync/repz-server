from datetime import datetime
from enum import StrEnum
from uuid import uuid4

from sqlalchemy import JSON, Boolean, DateTime, Enum, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ExerciseSource(StrEnum):
    WORKOUTX = "workoutx"
    CUSTOM = "custom"


class Exercise(Base):
    __tablename__ = "exercises"
    __table_args__ = (
        Index("ix_exercises_body_part", "body_part"),
        Index("ix_exercises_target", "target"),
        Index("ix_exercises_equipment", "equipment"),
        Index("ix_exercises_name_ft", "name", mysql_prefix="FULLTEXT"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    source: Mapped[ExerciseSource] = mapped_column(
        Enum(ExerciseSource, values_callable=lambda objs: [item.value for item in objs]),
        default=ExerciseSource.WORKOUTX,
    )
    external_id: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)
    name: Mapped[str] = mapped_column(String(255))
    body_part: Mapped[str | None] = mapped_column(String(128), nullable=True)
    target: Mapped[str | None] = mapped_column(String(128), nullable=True)
    equipment: Mapped[str | None] = mapped_column(String(128), nullable=True)
    secondary_muscles: Mapped[list | None] = mapped_column(JSON, nullable=True)
    instructions: Mapped[list | None] = mapped_column(JSON, nullable=True)
    gif_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    difficulty: Mapped[str | None] = mapped_column(String(64), nullable=True)
    mechanic: Mapped[str | None] = mapped_column(String(64), nullable=True)
    force: Mapped[str | None] = mapped_column(String(64), nullable=True)
    met: Mapped[float | None] = mapped_column(nullable=True)
    calories_per_minute: Mapped[float | None] = mapped_column(nullable=True)
    is_unilateral: Mapped[bool] = mapped_column(Boolean, default=False)
    recommended_sets: Mapped[str | None] = mapped_column(String(32), nullable=True)
    recommended_reps: Mapped[str | None] = mapped_column(String(32), nullable=True)
    movement_tags: Mapped[list | None] = mapped_column(JSON, nullable=True)
    created_by_user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True
    )
    is_time_based: Mapped[bool] = mapped_column(Boolean, default=False)
    is_distance_based: Mapped[bool] = mapped_column(Boolean, default=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    created_by = relationship("User")

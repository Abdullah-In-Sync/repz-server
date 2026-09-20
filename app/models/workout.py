from datetime import datetime
from enum import StrEnum
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class WorkoutSession(Base):
    __tablename__ = "workout_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    routine_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("routines.id"), nullable=True
    )
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    body_weight_kg: Mapped[float | None] = mapped_column(nullable=True)
    total_volume_kg: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user = relationship("User", back_populates="workouts")
    routine = relationship("Routine")
    sets = relationship("WorkoutSet", back_populates="session", cascade="all, delete-orphan")


class WorkoutSet(Base):
    __tablename__ = "workout_sets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    workout_session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workout_sessions.id"), index=True
    )
    exercise_id: Mapped[str] = mapped_column(String(36), ForeignKey("exercises.id"), index=True)
    set_number: Mapped[int] = mapped_column(Integer, default=1)
    weight_kg: Mapped[float | None] = mapped_column(nullable=True)
    reps: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rpe: Mapped[float | None] = mapped_column(nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    distance_km: Mapped[float | None] = mapped_column(nullable=True)
    is_warmup: Mapped[bool] = mapped_column(Boolean, default=False)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    session = relationship("WorkoutSession", back_populates="sets")
    exercise = relationship("Exercise")


class RecordType(StrEnum):
    MAX_WEIGHT = "max_weight"
    MAX_REPS = "max_reps"
    MAX_VOLUME = "max_volume"
    BEST_1RM = "best_1rm"
    LONGEST_DURATION = "longest_duration"
    LONGEST_DISTANCE = "longest_distance"


class PersonalRecord(Base):
    __tablename__ = "personal_records"
    __table_args__ = (
        UniqueConstraint("user_id", "exercise_id", "record_type", name="uq_pr_user_exercise_type"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    exercise_id: Mapped[str] = mapped_column(String(36), ForeignKey("exercises.id"), index=True)
    record_type: Mapped[RecordType] = mapped_column(
        Enum(RecordType, values_callable=lambda objs: [item.value for item in objs])
    )
    value: Mapped[float] = mapped_column(Float)
    achieved_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    workout_set_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("workout_sets.id"), nullable=True
    )

    exercise = relationship("Exercise")

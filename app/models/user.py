from datetime import date, datetime
from enum import StrEnum
from uuid import uuid4

from sqlalchemy import Date, DateTime, Enum, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class UnitPreference(StrEnum):
    KG = "kg"
    LB = "lb"


class Gender(StrEnum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"
    UNSPECIFIED = "unspecified"


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    firebase_uid: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    unit_preference: Mapped[UnitPreference] = mapped_column(
        Enum(UnitPreference, values_callable=lambda objs: [item.value for item in objs]),
        default=UnitPreference.KG,
    )
    timezone: Mapped[str] = mapped_column(String(64), default="UTC")
    height_cm: Mapped[float | None] = mapped_column(nullable=True)
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    gender: Mapped[Gender | None] = mapped_column(
        Enum(Gender, values_callable=lambda objs: [item.value for item in objs]),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    routines = relationship("Routine", back_populates="user", cascade="all, delete-orphan")
    workouts = relationship("WorkoutSession", back_populates="user", cascade="all, delete-orphan")

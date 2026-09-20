from datetime import datetime
from enum import StrEnum
from uuid import uuid4

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AchievementType(StrEnum):
    STREAK_7 = "streak_7"
    STREAK_30 = "streak_30"
    PR_BROKEN = "pr_broken"
    VOLUME_MILESTONE = "volume_milestone"
    CONSISTENCY_BADGE = "consistency_badge"


class Achievement(Base):
    __tablename__ = "achievements"
    __table_args__ = (
        UniqueConstraint("user_id", "type", "dedupe_key", name="uq_achievement_user_type_key"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    type: Mapped[AchievementType] = mapped_column(
        Enum(AchievementType, values_callable=lambda objs: [item.value for item in objs])
    )
    dedupe_key: Mapped[str] = mapped_column(String(128), default="default")
    metadata_json: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)
    unlocked_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

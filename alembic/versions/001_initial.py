"""initial schema

Revision ID: 001_initial
Revises:
Create Date: 2026-09-20
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("firebase_uid", sa.String(128), nullable=False),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("display_name", sa.String(255), nullable=True),
        sa.Column("avatar_url", sa.String(1024), nullable=True),
        sa.Column("unit_preference", sa.Enum("kg", "lb", name="unitpreference"), nullable=False),
        sa.Column("timezone", sa.String(64), nullable=False, server_default="UTC"),
        sa.Column("height_cm", sa.Float(), nullable=True),
        sa.Column("date_of_birth", sa.Date(), nullable=True),
        sa.Column("gender", sa.Enum("male", "female", "other", "unspecified", name="gender"), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_users_firebase_uid", "users", ["firebase_uid"], unique=True)

    op.create_table(
        "exercises",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("source", sa.Enum("workoutx", "custom", name="exercisesource"), nullable=False),
        sa.Column("external_id", sa.String(64), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("body_part", sa.String(128), nullable=True),
        sa.Column("target", sa.String(128), nullable=True),
        sa.Column("equipment", sa.String(128), nullable=True),
        sa.Column("secondary_muscles", sa.JSON(), nullable=True),
        sa.Column("instructions", sa.JSON(), nullable=True),
        sa.Column("gif_url", sa.String(1024), nullable=True),
        sa.Column("category", sa.String(64), nullable=True),
        sa.Column("difficulty", sa.String(64), nullable=True),
        sa.Column("mechanic", sa.String(64), nullable=True),
        sa.Column("force", sa.String(64), nullable=True),
        sa.Column("met", sa.Float(), nullable=True),
        sa.Column("calories_per_minute", sa.Float(), nullable=True),
        sa.Column("is_unilateral", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("recommended_sets", sa.String(32), nullable=True),
        sa.Column("recommended_reps", sa.String(32), nullable=True),
        sa.Column("movement_tags", sa.JSON(), nullable=True),
        sa.Column("created_by_user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("is_time_based", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_distance_based", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_exercises_external_id", "exercises", ["external_id"], unique=True)
    op.create_index("ix_exercises_body_part", "exercises", ["body_part"])
    op.create_index("ix_exercises_target", "exercises", ["target"])
    op.create_index("ix_exercises_equipment", "exercises", ["equipment"])
    op.create_index("ix_exercises_name_ft", "exercises", ["name"], mysql_prefix="FULLTEXT")

    op.create_table(
        "routines",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("folder", sa.String(128), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("last_used_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_routines_user_id", "routines", ["user_id"])

    op.create_table(
        "routine_exercises",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("routine_id", sa.String(36), sa.ForeignKey("routines.id"), nullable=False),
        sa.Column("exercise_id", sa.String(36), sa.ForeignKey("exercises.id"), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("target_sets", sa.Integer(), nullable=True),
        sa.Column("target_reps_range", sa.String(64), nullable=True),
        sa.Column("rest_seconds", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
    )
    op.create_index("ix_routine_exercises_routine_id", "routine_exercises", ["routine_id"])
    op.create_index("ix_routine_exercises_exercise_id", "routine_exercises", ["exercise_id"])

    op.create_table(
        "workout_sessions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("routine_id", sa.String(36), sa.ForeignKey("routines.id"), nullable=True),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column("started_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("ended_at", sa.DateTime(), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("body_weight_kg", sa.Float(), nullable=True),
        sa.Column("total_volume_kg", sa.Float(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_workout_sessions_user_id", "workout_sessions", ["user_id"])

    op.create_table(
        "workout_sets",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "workout_session_id",
            sa.String(36),
            sa.ForeignKey("workout_sessions.id"),
            nullable=False,
        ),
        sa.Column("exercise_id", sa.String(36), sa.ForeignKey("exercises.id"), nullable=False),
        sa.Column("set_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("weight_kg", sa.Float(), nullable=True),
        sa.Column("reps", sa.Integer(), nullable=True),
        sa.Column("rpe", sa.Float(), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("distance_km", sa.Float(), nullable=True),
        sa.Column("is_warmup", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_completed", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_workout_sets_session_id", "workout_sets", ["workout_session_id"])
    op.create_index("ix_workout_sets_exercise_id", "workout_sets", ["exercise_id"])

    op.create_table(
        "personal_records",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("exercise_id", sa.String(36), sa.ForeignKey("exercises.id"), nullable=False),
        sa.Column(
            "record_type",
            sa.Enum(
                "max_weight",
                "max_reps",
                "max_volume",
                "best_1rm",
                "longest_duration",
                "longest_distance",
                name="recordtype",
            ),
            nullable=False,
        ),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("achieved_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("workout_set_id", sa.String(36), sa.ForeignKey("workout_sets.id"), nullable=True),
        sa.UniqueConstraint("user_id", "exercise_id", "record_type", name="uq_pr_user_exercise_type"),
    )
    op.create_index("ix_personal_records_user_id", "personal_records", ["user_id"])
    op.create_index("ix_personal_records_exercise_id", "personal_records", ["exercise_id"])

    op.create_table(
        "body_metrics",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("weight_kg", sa.Float(), nullable=False),
        sa.Column("body_fat_pct", sa.Float(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_body_metrics_user_id", "body_metrics", ["user_id"])
    op.create_index("ix_body_metrics_date", "body_metrics", ["date"])

    op.create_table(
        "achievements",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "type",
            sa.Enum(
                "streak_7",
                "streak_30",
                "pr_broken",
                "volume_milestone",
                "consistency_badge",
                name="achievementtype",
            ),
            nullable=False,
        ),
        sa.Column("dedupe_key", sa.String(128), nullable=False, server_default="default"),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("unlocked_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", "type", "dedupe_key", name="uq_achievement_user_type_key"),
    )
    op.create_index("ix_achievements_user_id", "achievements", ["user_id"])

    op.create_table(
        "daily_stats",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("total_volume", sa.Float(), nullable=False, server_default="0"),
        sa.Column("total_sets", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("duration_seconds", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("calories_est", sa.Float(), nullable=False, server_default="0"),
        sa.UniqueConstraint("user_id", "date", name="uq_daily_stats_user_date"),
    )
    op.create_index("ix_daily_stats_user_id", "daily_stats", ["user_id"])
    op.create_index("ix_daily_stats_date", "daily_stats", ["date"])


def downgrade() -> None:
    op.drop_table("daily_stats")
    op.drop_table("achievements")
    op.drop_table("body_metrics")
    op.drop_table("personal_records")
    op.drop_table("workout_sets")
    op.drop_table("workout_sessions")
    op.drop_table("routine_exercises")
    op.drop_table("routines")
    op.drop_table("exercises")
    op.drop_table("users")

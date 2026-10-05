"""routine cardio target fields

Revision ID: 002_routine_cardio
Revises: 001_initial
Create Date: 2026-10-04

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002_routine_cardio"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "routine_exercises",
        sa.Column("target_duration_seconds", sa.Integer(), nullable=True),
    )
    op.add_column(
        "routine_exercises",
        sa.Column("target_distance_km", sa.Float(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("routine_exercises", "target_distance_km")
    op.drop_column("routine_exercises", "target_duration_seconds")

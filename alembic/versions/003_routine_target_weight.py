"""routine target weight

Revision ID: 003_routine_target_weight
Revises: 002_routine_cardio
Create Date: 2026-10-04

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003_routine_target_weight"
down_revision: Union[str, None] = "002_routine_cardio"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "routine_exercises",
        sa.Column("target_weight_kg", sa.Float(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("routine_exercises", "target_weight_kg")

"""routine per-set targets

Revision ID: 004_routine_set_targets
Revises: 003_routine_target_weight
Create Date: 2026-10-04

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004_routine_set_targets"
down_revision: Union[str, None] = "003_routine_target_weight"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "routine_exercises",
        sa.Column("set_targets", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("routine_exercises", "set_targets")

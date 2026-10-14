"""add comparison tool capability

Revision ID: b7c2f4a91e63
Revises: a3d5e8b1c740
Create Date: 2026-07-29 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b7c2f4a91e63"
down_revision: Union[str, Sequence[str], None] = "a3d5e8b1c740"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "comparison",
        sa.Column("tool_capable_a", sa.Boolean(), nullable=True),
    )
    op.add_column(
        "comparison",
        sa.Column("tool_capable_b", sa.Boolean(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("comparison", "tool_capable_b")
    op.drop_column("comparison", "tool_capable_a")

"""add agent stop reason

Revision ID: a3d5e8b1c740
Revises: f2c8d1a6b4e9
Create Date: 2026-07-29 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a3d5e8b1c740"
down_revision: Union[str, Sequence[str], None] = "f2c8d1a6b4e9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "llm_message",
        sa.Column("agent_stop_reason", sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("llm_message", "agent_stop_reason")

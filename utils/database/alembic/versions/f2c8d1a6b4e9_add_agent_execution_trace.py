"""add agent execution trace

Revision ID: f2c8d1a6b4e9
Revises: e4b7a9c2d6f1
Create Date: 2026-07-27 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "f2c8d1a6b4e9"
down_revision: Union[str, Sequence[str], None] = "e4b7a9c2d6f1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "llm_message",
        sa.Column(
            "agent_trace",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("llm_message", "agent_trace")

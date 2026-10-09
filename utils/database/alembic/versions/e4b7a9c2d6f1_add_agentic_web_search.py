"""add agentic web search fields

Revision ID: e4b7a9c2d6f1
Revises: c6a1f3e8d2b7
Create Date: 2026-07-27 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "e4b7a9c2d6f1"
down_revision: Union[str, Sequence[str], None] = "c6a1f3e8d2b7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "comparison",
        sa.Column(
            "web_search_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.alter_column("comparison", "web_search_enabled", server_default=None)
    op.add_column(
        "llm_message",
        sa.Column(
            "web_search_results",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("llm_message", "web_search_results")
    op.drop_column("comparison", "web_search_enabled")

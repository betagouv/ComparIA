"""replace web search flag with tool selection

Revision ID: e5a91c73f2d8
Revises: d4f8b2c15a09
Create Date: 2026-07-29 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "e5a91c73f2d8"
down_revision: Union[str, Sequence[str], None] = "d4f8b2c15a09"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "comparison",
        sa.Column(
            "enabled_tools",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
        ),
    )
    # A comparison that had web search on becomes one that selected that tool.
    op.execute(
        """
        UPDATE comparison
        SET enabled_tools = '["web_search"]'::jsonb
        WHERE web_search_enabled IS TRUE
        """
    )
    op.drop_column("comparison", "web_search_enabled")


def downgrade() -> None:
    op.add_column(
        "comparison",
        sa.Column(
            "web_search_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.execute(
        """
        UPDATE comparison
        SET web_search_enabled = TRUE
        WHERE enabled_tools @> '["web_search"]'::jsonb
        """
    )
    op.drop_column("comparison", "enabled_tools")

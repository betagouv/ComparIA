"""add_statistics_query_indexes

Revision ID: f3b8c1d2e4a5
Revises: b3d1c7a4e9f2
Create Date: 2026-08-05 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f3b8c1d2e4a5"
down_revision: Union[str, Sequence[str], None] = "b3d1c7a4e9f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.create_index(
            "ix_comparison_statistics_created_at",
            "comparison",
            ["created_at"],
            unique=False,
            postgresql_where=sa.text("archived IS NOT TRUE"),
            postgresql_include=["llm_id_a", "llm_id_b"],
            postgresql_concurrently=True,
        )
        op.create_index(
            "ix_turn_statistics_created_at_comparison_id",
            "turn",
            ["created_at", "comparison_id"],
            unique=False,
            postgresql_concurrently=True,
        )


def downgrade() -> None:
    with op.get_context().autocommit_block():
        op.drop_index(
            "ix_turn_statistics_created_at_comparison_id",
            table_name="turn",
            postgresql_concurrently=True,
        )
        op.drop_index(
            "ix_comparison_statistics_created_at",
            table_name="comparison",
            postgresql_concurrently=True,
        )

"""add tool

Revision ID: c9e1a7d34b52
Revises: b7c2f4a91e63
Create Date: 2026-07-29 00:00:00.000000

"""

import uuid
from datetime import datetime
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c9e1a7d34b52"
down_revision: Union[str, Sequence[str], None] = "b7c2f4a91e63"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    tool = op.create_table(
        "tool",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("key", sa.String(), nullable=False),
        sa.Column("label", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tool_key", "tool", ["key"], unique=True)

    # Web search already existed in code; it becomes the first configured row so
    # that upgrading an instance does not silently take it away.
    op.bulk_insert(
        tool,
        [
            {
                "id": uuid.uuid4(),
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
                "key": "web_search",
                "label": "Recherche web",
                "description": "Chercher des informations récentes sur le web.",
                "kind": "builtin",
                "enabled": True,
            }
        ],
    )


def downgrade() -> None:
    op.drop_index("ix_tool_key", table_name="tool")
    op.drop_table("tool")

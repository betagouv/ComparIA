"""add mcp tools

Revision ID: d4f8b2c15a09
Revises: c9e1a7d34b52
Create Date: 2026-07-29 00:00:00.000000

"""

import uuid
from datetime import datetime
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d4f8b2c15a09"
down_revision: Union[str, Sequence[str], None] = "c9e1a7d34b52"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("tool", sa.Column("url", sa.String(), nullable=True))
    op.add_column("tool", sa.Column("auth_header", sa.String(), nullable=True))

    # bulk_insert binds values rather than compiling them, so a SQL function
    # here would reach the driver as an object it cannot adapt.
    now = datetime.now()

    # Disabled on arrival: switching it on is an editorial decision, not the
    # side effect of an upgrade.
    op.bulk_insert(
        sa.table(
            "tool",
            sa.column("id", sa.Uuid()),
            sa.column("created_at", sa.DateTime()),
            sa.column("updated_at", sa.DateTime()),
            sa.column("key", sa.String()),
            sa.column("label", sa.String()),
            sa.column("description", sa.String()),
            sa.column("kind", sa.String()),
            sa.column("url", sa.String()),
            sa.column("auth_header", sa.String()),
            sa.column("enabled", sa.Boolean()),
        ),
        [
            {
                "id": uuid.uuid4(),
                "created_at": now,
                "updated_at": now,
                "key": "datagouv",
                "label": "Données publiques",
                "description": (
                    "Chercher des jeux de données publics sur data.gouv.fr."
                ),
                "kind": "mcp",
                "url": "https://mcp.data.gouv.fr/mcp",
                "auth_header": None,
                "enabled": False,
            }
        ],
    )


def downgrade() -> None:
    op.execute("DELETE FROM tool WHERE key = 'datagouv'")
    op.drop_column("tool", "auth_header")
    op.drop_column("tool", "url")

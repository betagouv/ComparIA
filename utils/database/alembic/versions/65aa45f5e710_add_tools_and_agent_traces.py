"""add tools and agent traces

Revision ID: 65aa45f5e710
Revises: b5d9e3f7a1c2
Create Date: 2026-11-25 13:06:33.602619

"""

import uuid
from datetime import datetime
from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "65aa45f5e710"
down_revision: Union[str, Sequence[str], None] = "b5d9e3f7a1c2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    tool = op.create_table(
        "tool",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", postgresql.TIMESTAMP(), nullable=False),
        sa.Column("updated_at", postgresql.TIMESTAMP(), nullable=False),
        sa.Column("key", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("label", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("description", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("url", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column(
            "allowed_functions",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "allowed_domains", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column(
            "blocked_domains", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column(
            "secret_encrypted", sqlmodel.sql.sqltypes.AutoString(), nullable=True
        ),
        sa.Column("logo", sa.LargeBinary(), nullable=True),
        sa.Column(
            "logo_content_type", sqlmodel.sql.sqltypes.AutoString(), nullable=True
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_tool_key"), "tool", ["key"], unique=True)
    # Existing comparisons selected no tool.
    op.add_column(
        "comparison",
        sa.Column(
            "enabled_tools",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
        ),
    )
    op.add_column(
        "comparison", sa.Column("tool_capable_a", sa.Boolean(), nullable=True)
    )
    op.add_column(
        "comparison", sa.Column("tool_capable_b", sa.Boolean(), nullable=True)
    )
    op.add_column(
        "llm_message",
        sa.Column(
            "agent_trace", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
    )
    op.add_column(
        "llm_message", sa.Column("agent_stop_reason", sa.String(), nullable=True)
    )

    # Every tool starts switched off: tools send queries written from visitor
    # prompts to outside services, so an admin turns each one on deliberately.
    # bulk_insert binds values rather than compiling them, so a SQL function
    # here would reach the driver as an object it cannot adapt.
    now = datetime.now()
    op.bulk_insert(
        tool,
        [
            {
                "id": uuid.uuid4(),
                "created_at": now,
                "updated_at": now,
                "key": "web_search",
                "label": "Recherche web",
                "description": "Chercher des informations récentes sur le web.",
                "kind": "builtin",
                "url": None,
                "enabled": False,
            },
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
                "enabled": False,
            },
        ],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("llm_message", "agent_stop_reason")
    op.drop_column("llm_message", "agent_trace")
    op.drop_column("comparison", "tool_capable_b")
    op.drop_column("comparison", "tool_capable_a")
    op.drop_column("comparison", "enabled_tools")
    op.drop_index(op.f("ix_tool_key"), table_name="tool")
    op.drop_table("tool")

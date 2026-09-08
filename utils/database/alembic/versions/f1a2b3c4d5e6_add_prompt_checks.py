"""add_prompt_checks

Creates the prompt_check singleton holding the per-category thresholds and
actions applied to a user prompt before it reaches the arena models.

Revision ID: f1a2b3c4d5e6
Revises: f3b8c1d2e4a5
Create Date: 2026-07-31 00:00:00.000000

"""

from datetime import datetime
from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel
from alembic import op
from sqlalchemy.dialects import postgresql

from utils.database.models.prompt_check import DEFAULT_CATEGORIES, DEFAULT_MODEL

# revision identifiers, used by Alembic.
revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, Sequence[str], None] = "f3b8c1d2e4a5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    prompt_check = op.create_table(
        "prompt_check",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("api_key", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column(
            "model",
            sqlmodel.sql.sqltypes.AutoString(),
            nullable=False,
            server_default=DEFAULT_MODEL,
        ),
        sa.Column("categories", postgresql.JSONB(), nullable=False),
        sa.Column("updated_at", postgresql.TIMESTAMP(), nullable=False),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(["updated_by"], ["auth_user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # Every category starts on log. Nothing is refused or shown to anyone until
    # an admin has watched the verdicts on real traffic.
    op.bulk_insert(
        prompt_check,
        [
            {
                "id": 1,
                "enabled": True,
                "model": DEFAULT_MODEL,
                "categories": DEFAULT_CATEGORIES,
                "updated_at": datetime.now(),
            }
        ],
    )

    # Turn.guardrail is deliberately left alone. Rows written by the Nemotron
    # guardrail keep its record; new rows get the new one. Both are a single
    # JSON object on the turn, the column is raw-only, and nothing reads it yet.
    op.create_index(
        "ix_turn_prompt_check_created_at",
        "turn",
        ["created_at"],
        postgresql_where=sa.text("guardrail ? 'decision'"),
    )


def downgrade() -> None:
    op.drop_index("ix_turn_prompt_check_created_at", table_name="turn")
    op.drop_table("prompt_check")

"""add_prompt_checks

Creates the prompt_check table with its two seeded rows, and reshapes
Turn.guardrail from a single verdict into one entry per check.

Revision ID: f1a2b3c4d5e6
Revises: e8f7a6b5c4d3
Create Date: 2026-07-31 00:00:00.000000

"""

from datetime import datetime
from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel
from alembic import op
from sqlalchemy.dialects import postgresql

from utils.database.models.prompt_check import DEFAULT_MODEL, DEFAULT_THRESHOLDS

# revision identifiers, used by Alembic.
revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, Sequence[str], None] = "e8f7a6b5c4d3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    prompt_check = op.create_table(
        "prompt_check",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("mode", sa.String(), nullable=False, server_default="log"),
        sa.Column("thresholds", postgresql.JSONB(), nullable=False),
        sa.Column(
            "model",
            sqlmodel.sql.sqltypes.AutoString(),
            nullable=False,
            server_default=DEFAULT_MODEL,
        ),
        sa.Column("updated_at", postgresql.TIMESTAMP(), nullable=False),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(["updated_by"], ["auth_user.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("kind"),
    )
    op.create_index("ix_prompt_check_kind", "prompt_check", ["kind"])

    # Both checks start in log mode. Nothing is refused until an admin has
    # looked at the verdicts on real traffic.
    seeded_at = datetime.now()
    op.bulk_insert(
        prompt_check,
        [
            {
                "id": index,
                "kind": kind,
                "mode": "log",
                "thresholds": DEFAULT_THRESHOLDS[kind],
                "model": DEFAULT_MODEL,
                "updated_at": seeded_at,
            }
            for index, kind in enumerate(("content_safety", "pii"), start=1)
        ],
    )

    # Existing verdicts were written by the Nemotron guardrail, which was the
    # only check. Nest them so the column has one shape.
    op.execute("""
        UPDATE turn
        SET guardrail = jsonb_build_object('content_safety', guardrail)
        WHERE guardrail IS NOT NULL
          AND NOT (guardrail ? 'content_safety')
        """)


def downgrade() -> None:
    op.execute("""
        UPDATE turn
        SET guardrail = guardrail -> 'content_safety'
        WHERE guardrail IS NOT NULL
          AND guardrail ? 'content_safety'
        """)
    op.drop_index("ix_prompt_check_kind", table_name="prompt_check")
    op.drop_table("prompt_check")

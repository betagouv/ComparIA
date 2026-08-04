"""add_publish_schedule_and_runs

Revision ID: e2c4b9a7f631
Revises: d7b3e6a1c852
Create Date: 2026-08-04 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "e2c4b9a7f631"
down_revision: Union[str, Sequence[str], None] = "d7b3e6a1c852"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 'off' on every existing instance: turning the schedule on is a decision
    # an administrator takes, not something an upgrade takes for them.
    op.add_column(
        "app_settings",
        sa.Column(
            "publish_frequency",
            sa.String(length=20),
            nullable=False,
            server_default="off",
        ),
    )
    op.add_column(
        "app_settings",
        sa.Column("publish_hour", sa.Integer(), nullable=False, server_default="3"),
    )
    op.add_column(
        "app_settings",
        sa.Column(
            "publish_timezone",
            sa.String(length=64),
            nullable=False,
            server_default="UTC",
        ),
    )

    op.create_table(
        "publish_run",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", postgresql.TIMESTAMP(), nullable=False),
        sa.Column("updated_at", postgresql.TIMESTAMP(), nullable=False),
        sa.Column("started_at", postgresql.TIMESTAMP(), nullable=False),
        sa.Column("finished_at", postgresql.TIMESTAMP(), nullable=True),
        sa.Column("succeeded", sa.Boolean(), nullable=True),
        sa.Column("error", sa.String(), nullable=True),
        sa.Column("held_back", sa.Integer(), nullable=True),
        sa.Column("comparisons", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("publish_run")
    op.drop_column("app_settings", "publish_timezone")
    op.drop_column("app_settings", "publish_hour")
    op.drop_column("app_settings", "publish_frequency")

"""add publish request and last run to destinations

Revision ID: b3d7a1c9e5f2
Revises: 269a5fc3959c
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "b3d7a1c9e5f2"
down_revision: str | None = "269a5fc3959c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "publish_destination",
        sa.Column("publish_requested_at", postgresql.TIMESTAMP(), nullable=True),
    )
    op.add_column(
        "publish_destination",
        sa.Column("last_run_started_at", postgresql.TIMESTAMP(), nullable=True),
    )
    # The publish job runs whatever occurrence is later than the last run. Left
    # empty, every scheduled destination would be due at the first tick after
    # the deployment, in the middle of the day.
    op.execute("""
        UPDATE publish_destination
        SET last_run_started_at = COALESCE(
            (SELECT max(started_at) FROM publish_run),
            now() AT TIME ZONE 'utc'
        )
        """)


def downgrade() -> None:
    op.drop_column("publish_destination", "last_run_started_at")
    op.drop_column("publish_destination", "publish_requested_at")

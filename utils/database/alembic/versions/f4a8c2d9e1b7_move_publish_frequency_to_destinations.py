"""move publish frequency to destinations

Revision ID: f4a8c2d9e1b7
Revises: e2c4b9a7f631
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f4a8c2d9e1b7"
down_revision: str | None = "e2c4b9a7f631"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "publish_destination",
        sa.Column(
            "publish_frequency", sa.String(), nullable=False, server_default="off"
        ),
    )
    op.execute("""
        UPDATE publish_destination
        SET publish_frequency = app_settings.publish_frequency
        FROM app_settings
        WHERE app_settings.id = 1
        """)


def downgrade() -> None:
    op.drop_column("publish_destination", "publish_frequency")

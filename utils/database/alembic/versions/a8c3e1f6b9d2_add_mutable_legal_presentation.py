"""add mutable legal presentation settings

Revision ID: a8c3e1f6b9d2
Revises: f7b2d4a9c6e1
Create Date: 2026-07-20 17:45:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "a8c3e1f6b9d2"
down_revision: Union[str, Sequence[str], None] = "f7b2d4a9c6e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "app_settings",
        sa.Column("legal_presentation", postgresql.JSONB(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("app_settings", "legal_presentation")

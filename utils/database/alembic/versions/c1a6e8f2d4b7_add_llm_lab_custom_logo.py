"""add llm lab custom logo

Revision ID: c1a6e8f2d4b7
Revises: b7e3c9a1d5f2
Create Date: 2026-08-26 00:00:00.000000
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "c1a6e8f2d4b7"
down_revision: str | Sequence[str] | None = "b7e3c9a1d5f2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("llm_lab", sa.Column("logo_data", sa.LargeBinary(), nullable=True))
    op.add_column("llm_lab", sa.Column("logo_content_type", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("llm_lab", "logo_content_type")
    op.drop_column("llm_lab", "logo_data")

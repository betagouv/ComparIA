"""add Turn.voted_at

Revision ID: a3f7c1e9b2d4
Revises: 67e629fed515
Create Date: 2026-06-08 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'a3f7c1e9b2d4'
down_revision: Union[str, Sequence[str], None] = '67e629fed515'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'turn',
        sa.Column('voted_at', postgresql.TIMESTAMP(), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('turn', 'voted_at')

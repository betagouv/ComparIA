"""add matomo enabled

Revision ID: 4d548a0b71cf
Revises: b7c3e9d1a2f4
Create Date: 2026-11-26 12:46:34.056263

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '4d548a0b71cf'
down_revision: Union[str, Sequence[str], None] = 'b7c3e9d1a2f4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Null follows the frontend server's environment, so every instance keeps
    # measuring as it did before.
    op.add_column('app_settings', sa.Column('matomo_enabled', sa.Boolean(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('app_settings', 'matomo_enabled')

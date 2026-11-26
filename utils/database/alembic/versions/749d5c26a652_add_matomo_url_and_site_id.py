"""add matomo url and site id

Revision ID: 749d5c26a652
Revises: 4d548a0b71cf
Create Date: 2026-11-26 12:55:45.147310

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel

# revision identifiers, used by Alembic.
revision: str = '749d5c26a652'
down_revision: Union[str, Sequence[str], None] = '4d548a0b71cf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Read only when matomo_enabled is true, so every instance keeps
    # measuring as it did before.
    op.add_column('app_settings', sa.Column('matomo_url', sqlmodel.sql.sqltypes.AutoString(length=2048), nullable=True))
    op.add_column('app_settings', sa.Column('matomo_site_id', sqlmodel.sql.sqltypes.AutoString(length=32), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('app_settings', 'matomo_site_id')
    op.drop_column('app_settings', 'matomo_url')

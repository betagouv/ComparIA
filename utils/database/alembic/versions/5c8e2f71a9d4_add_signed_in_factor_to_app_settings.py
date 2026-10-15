"""add_signed_in_factor_to_app_settings

Revision ID: 5c8e2f71a9d4
Revises: 1bdbe90c7e4c
Create Date: 2026-10-15 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5c8e2f71a9d4'
down_revision: Union[str, Sequence[str], None] = '1bdbe90c7e4c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Empty: the RATELIMIT_SIGNED_IN_FACTOR default holds until an admin sets
    # one.
    op.add_column(
        'app_settings',
        sa.Column('limit_signed_in_factor', sa.Float(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('app_settings', 'limit_signed_in_factor')

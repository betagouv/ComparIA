"""add_in_flight_limit_to_app_settings

Revision ID: 1bdbe90c7e4c
Revises: 8db1ac83a809
Create Date: 2026-10-14 21:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1bdbe90c7e4c'
down_revision: Union[str, Sequence[str], None] = '8db1ac83a809'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Empty: the RATELIMIT_IN_FLIGHT_PER_NETWORK default holds until an admin
    # sets one.
    op.add_column(
        'app_settings',
        sa.Column('limit_in_flight_per_network', sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('app_settings', 'limit_in_flight_per_network')

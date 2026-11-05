"""add_ranking_grey_rank_spread

Revision ID: e3b7d9a2c4f1
Revises: a8c3f1e6d2b9
Create Date: 2026-11-04 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'e3b7d9a2c4f1'
down_revision: Union[str, Sequence[str], None] = 'a8c3f1e6d2b9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Backfilled with the default hide threshold, so no model is greyed out on
    # upgrade until an admin lowers it.
    op.add_column(
        'app_settings',
        sa.Column(
            'ranking_grey_rank_spread', sa.Integer(), nullable=False, server_default='30'
        ),
    )
    op.alter_column('app_settings', 'ranking_grey_rank_spread', server_default=None)


def downgrade() -> None:
    op.drop_column('app_settings', 'ranking_grey_rank_spread')

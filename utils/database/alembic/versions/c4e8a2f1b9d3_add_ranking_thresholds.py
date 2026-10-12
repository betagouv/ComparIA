"""add_ranking_thresholds

Revision ID: c4e8a2f1b9d3
Revises: a3d6f1c9e842
Create Date: 2026-10-12 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'c4e8a2f1b9d3'
down_revision: Union[str, Sequence[str], None] = 'a3d6f1c9e842'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Backfilled with the values the leaderboard used before they were
    # settings, so no instance's ranking changes on upgrade.
    op.add_column(
        'app_settings',
        sa.Column('ranking_min_votes', sa.Integer(), nullable=False, server_default='0'),
    )
    op.add_column(
        'app_settings',
        sa.Column(
            'ranking_max_rank_spread', sa.Integer(), nullable=False, server_default='30'
        ),
    )
    op.alter_column('app_settings', 'ranking_min_votes', server_default=None)
    op.alter_column('app_settings', 'ranking_max_rank_spread', server_default=None)


def downgrade() -> None:
    op.drop_column('app_settings', 'ranking_max_rank_spread')
    op.drop_column('app_settings', 'ranking_min_votes')

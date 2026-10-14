"""add_expensive_paused_to_comparison

Revision ID: 84f4becbdc4c
Revises: 7181adf67155
Create Date: 2026-10-14 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '84f4becbdc4c'
down_revision: Union[str, Sequence[str], None] = '7181adf67155'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Every comparison so far was drawn with expensive models open. The
    # default also lets the pods still running during the upgrade insert rows
    # without the column.
    op.add_column(
        'comparison',
        sa.Column(
            'expensive_paused', sa.Boolean(), nullable=False, server_default=sa.false()
        ),
    )


def downgrade() -> None:
    op.drop_column('comparison', 'expensive_paused')

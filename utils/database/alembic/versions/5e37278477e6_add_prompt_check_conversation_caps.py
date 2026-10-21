"""add prompt_check conversation caps

Revision ID: 5e37278477e6
Revises: 2b82412c4f91
Create Date: 2026-10-21 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '5e37278477e6'
down_revision: Union[str, Sequence[str], None] = '2b82412c4f91'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Null means the RATELIMIT_CONVERSATIONS_* settings apply, so no row needs
    # to be rewritten and an instance keeps its current behaviour.
    op.add_column(
        'prompt_check',
        sa.Column('conversations_per_ip_per_hour', sa.Integer(), nullable=True),
    )
    op.add_column(
        'prompt_check',
        sa.Column(
            'conversations_same_models_per_ip_per_hour', sa.Integer(), nullable=True
        ),
    )


def downgrade() -> None:
    op.drop_column('prompt_check', 'conversations_same_models_per_ip_per_hour')
    op.drop_column('prompt_check', 'conversations_per_ip_per_hour')

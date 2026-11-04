"""add comparison reservation dates

Revision ID: 419fdfa45498
Revises: a8c3f1e6d2b9
Create Date: 2026-10-26 16:09:40.659855

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '419fdfa45498'
down_revision: Union[str, Sequence[str], None] = 'a8c3f1e6d2b9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'comparison', sa.Column('reserved_at', postgresql.TIMESTAMP(), nullable=True)
    )
    op.add_column(
        'comparison',
        sa.Column('first_reserved_at', postgresql.TIMESTAMP(), nullable=True),
    )
    # A few hundred rows out of millions: the publishing page counts them on
    # every visit, and the conversation list filters on them.
    op.create_index(
        'ix_comparison_reserved_at',
        'comparison',
        ['reserved_at'],
        postgresql_where=sa.text('reserved_at IS NOT NULL'),
    )


def downgrade() -> None:
    op.drop_index('ix_comparison_reserved_at', table_name='comparison')
    op.drop_column('comparison', 'first_reserved_at')
    op.drop_column('comparison', 'reserved_at')

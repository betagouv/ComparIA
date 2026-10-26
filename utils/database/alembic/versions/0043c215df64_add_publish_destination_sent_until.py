"""add publish_destination sent_until

Revision ID: 0043c215df64
Revises: 0e1680903d6f
Create Date: 2026-10-26 16:12:07.612946

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0043c215df64'
down_revision: Union[str, Sequence[str], None] = '0e1680903d6f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'publish_destination',
        sa.Column('sent_until', postgresql.TIMESTAMP(), nullable=True),
    )
    # A destination that ran before the column existed may have sent anything
    # created until now: its last start is too early, a run that was building
    # then still picked up newer comparisons.
    op.execute(
        """
        UPDATE publish_destination
        SET sent_until = timezone('utc', now())
        WHERE last_run_started_at IS NOT NULL
        """
    )


def downgrade() -> None:
    op.drop_column('publish_destination', 'sent_until')

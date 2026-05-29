"""merge_drop_session_hash_and_remove_unique_constraint

Revision ID: 67e629fed515
Revises: 88e025e5dbfa, 137fbd6418e6
Create Date: 2026-05-20 15:47:29.640824

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = '67e629fed515'
down_revision: Union[str, Sequence[str], None] = ('88e025e5dbfa', '137fbd6418e6')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass

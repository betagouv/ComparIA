"""merge ranking thresholds and tool message index

Revision ID: 1a3708d16951
Revises: a375433e6a93, c4e8a2f1b9d3
Create Date: 2026-10-14 12:55:47.586689

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = '1a3708d16951'
down_revision: Union[str, Sequence[str], None] = ('a375433e6a93', 'c4e8a2f1b9d3')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass

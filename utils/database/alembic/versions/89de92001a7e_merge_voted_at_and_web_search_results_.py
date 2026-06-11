"""merge voted_at and web_search_results heads

Revision ID: 89de92001a7e
Revises: a3f7c1e9b2d4, d9b83b7f2988
Create Date: 2026-06-11 16:25:05.997998

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = '89de92001a7e'
down_revision: Union[str, Sequence[str], None] = ('a3f7c1e9b2d4', 'd9b83b7f2988')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass

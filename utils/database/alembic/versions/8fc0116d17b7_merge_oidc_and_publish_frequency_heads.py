"""merge_oidc_publish_frequency_and_vote_tags_heads

Revision ID: 8fc0116d17b7
Revises: a1b2c3d4e5f6, b3d1c7a4e9f2, f4a8c2d9e1b7
Create Date: 2026-08-12 12:55:00.159381

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = '8fc0116d17b7'
down_revision: Union[str, Sequence[str], None] = ('a1b2c3d4e5f6', 'b3d1c7a4e9f2', 'f4a8c2d9e1b7')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass

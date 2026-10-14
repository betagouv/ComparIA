"""merge oidc connection test and tool selection

Revision ID: a05512fa3efe
Revises: a3d6f1c9e842, e5a91c73f2d8
Create Date: 2026-10-08 10:57:31.443015

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = 'a05512fa3efe'
down_revision: Union[str, Sequence[str], None] = ('a3d6f1c9e842', 'e5a91c73f2d8')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass

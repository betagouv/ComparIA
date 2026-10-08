"""merge totp, publish request and oidc heads

Revision ID: 5c8bd69940b5
Revises: 6793ef0ce18c, a9c4e2f7b1d3, b3d7a1c9e5f2
Create Date: 2026-09-30 11:28:13.911563

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = '5c8bd69940b5'
down_revision: Union[str, Sequence[str], None] = ('6793ef0ce18c', 'a9c4e2f7b1d3', 'b3d7a1c9e5f2')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass

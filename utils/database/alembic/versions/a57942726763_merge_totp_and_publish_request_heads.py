"""merge totp and publish request heads

Revision ID: a57942726763
Revises: a9c4e2f7b1d3, b3d7a1c9e5f2
Create Date: 2026-10-06 15:35:12.426781

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = 'a57942726763'
down_revision: Union[str, Sequence[str], None] = ('a9c4e2f7b1d3', 'b3d7a1c9e5f2')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass

"""add user inactivity_warned_at

Revision ID: 58abc2a23978
Revises: 269a5fc3959c
Create Date: 2026-09-15 17:04:06.864130

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '58abc2a23978'
down_revision: Union[str, Sequence[str], None] = '269a5fc3959c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'auth_user',
        sa.Column('inactivity_warned_at', postgresql.TIMESTAMP(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('auth_user', 'inactivity_warned_at')

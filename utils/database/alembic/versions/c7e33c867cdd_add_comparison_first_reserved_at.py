"""add comparison first_reserved_at

Revision ID: c7e33c867cdd
Revises: 60128c026929
Create Date: 2026-10-26 17:12:08.880934

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'c7e33c867cdd'
down_revision: Union[str, Sequence[str], None] = '60128c026929'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'comparison',
        sa.Column('first_reserved_at', postgresql.TIMESTAMP(), nullable=True),
    )
    op.execute(
        "UPDATE comparison SET first_reserved_at = reserved_at"
        " WHERE reserved_at IS NOT NULL"
    )


def downgrade() -> None:
    op.drop_column('comparison', 'first_reserved_at')

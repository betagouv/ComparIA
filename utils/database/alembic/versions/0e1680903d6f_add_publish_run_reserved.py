"""add publish_run reserved

Revision ID: 0e1680903d6f
Revises: 419fdfa45498
Create Date: 2026-10-26 16:14:02.118204

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '0e1680903d6f'
down_revision: Union[str, Sequence[str], None] = '419fdfa45498'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('publish_run', sa.Column('reserved', sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column('publish_run', 'reserved')

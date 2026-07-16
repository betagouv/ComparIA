"""add_terms_content

Revision ID: 18473f43cb78
Revises: c6a1f3e8d2b7
Create Date: 2026-07-16 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel

# revision identifiers, used by Alembic.
revision: str = '18473f43cb78'
down_revision: Union[str, Sequence[str], None] = 'c6a1f3e8d2b7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'app_settings',
        sa.Column('terms_content', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('app_settings', 'terms_content')

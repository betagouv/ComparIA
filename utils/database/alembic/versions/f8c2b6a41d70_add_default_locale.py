"""add_default_locale

Revision ID: f8c2b6a41d70
Revises: e3a7c5f19b04
Create Date: 2026-07-21 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel

# revision identifiers, used by Alembic.
revision: str = 'f8c2b6a41d70'
down_revision: Union[str, Sequence[str], None] = 'e3a7c5f19b04'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'app_settings',
        sa.Column(
            'default_locale',
            sqlmodel.sql.sqltypes.AutoString(),
            nullable=False,
            server_default='fr',
        ),
    )
    op.alter_column('app_settings', 'default_locale', server_default=None)


def downgrade() -> None:
    op.drop_column('app_settings', 'default_locale')

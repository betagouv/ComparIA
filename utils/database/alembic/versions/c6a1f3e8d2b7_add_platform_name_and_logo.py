"""add_platform_name_and_logo

Revision ID: c6a1f3e8d2b7
Revises: b4e5d9c86405
Create Date: 2026-07-10 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel

# revision identifiers, used by Alembic.
revision: str = 'c6a1f3e8d2b7'
down_revision: Union[str, Sequence[str], None] = 'b4e5d9c86405'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'app_settings',
        sa.Column(
            'platform_name',
            sqlmodel.sql.sqltypes.AutoString(),
            nullable=False,
            server_default='Compar:IA',
        ),
    )
    op.add_column('app_settings', sa.Column('logo', sa.LargeBinary(), nullable=True))
    op.add_column(
        'app_settings',
        sa.Column('logo_content_type', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    )
    op.alter_column('app_settings', 'platform_name', server_default=None)


def downgrade() -> None:
    op.drop_column('app_settings', 'logo_content_type')
    op.drop_column('app_settings', 'logo')
    op.drop_column('app_settings', 'platform_name')

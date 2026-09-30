"""add_user_role

Revision ID: d1f4a2e7c9b5
Revises: b2d4a7e9c1f3
Create Date: 2026-06-25 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel
from alembic import op

revision: str = 'd1f4a2e7c9b5'
down_revision: Union[str, Sequence[str], None] = 'b2d4a7e9c1f3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'auth_user',
        sa.Column(
            'role',
            sqlmodel.sql.sqltypes.AutoString(),
            nullable=False,
            server_default='user',
        ),
    )


def downgrade() -> None:
    op.drop_column('auth_user', 'role')

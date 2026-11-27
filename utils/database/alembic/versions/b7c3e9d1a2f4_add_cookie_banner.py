"""add cookie banner

Revision ID: b7c3e9d1a2f4
Revises: 60128c026929
Create Date: 2026-11-25 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'b7c3e9d1a2f4'
down_revision: Union[str, Sequence[str], None] = '60128c026929'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Off on every instance until an admin turns it on. With no text stored,
    # visitors read the default banner held in code.
    op.add_column(
        'app_settings',
        sa.Column(
            'cookie_banner_enabled',
            sa.Boolean(),
            nullable=False,
            server_default='false',
        ),
    )
    op.alter_column('app_settings', 'cookie_banner_enabled', server_default=None)
    op.add_column(
        'app_settings',
        sa.Column('cookie_banner', postgresql.JSONB(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('app_settings', 'cookie_banner')
    op.drop_column('app_settings', 'cookie_banner_enabled')

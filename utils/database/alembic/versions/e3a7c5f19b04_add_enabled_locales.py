"""add_enabled_locales

Revision ID: e3a7c5f19b04
Revises: d4f9a1c7e2b8
Create Date: 2026-07-21 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'e3a7c5f19b04'
down_revision: Union[str, Sequence[str], None] = 'd4f9a1c7e2b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'app_settings',
        sa.Column(
            'enabled_locales',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default='["da", "en", "fr", "lt", "sv"]',
        ),
    )
    op.alter_column('app_settings', 'enabled_locales', server_default=None)


def downgrade() -> None:
    op.drop_column('app_settings', 'enabled_locales')

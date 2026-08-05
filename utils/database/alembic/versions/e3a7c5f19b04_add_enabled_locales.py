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


# Frozen copy of DEFAULT_ENABLED_LOCALES at the time of this revision. Migrations
# don't import app code, so this stays right even after the model's list moves on.
# lt and sv are left out on purpose: this reproduces the PUBLIC_DISABLED_LOCALES
# ="lt,sv" both instances were deployed with, so nobody gains a half-translated
# language on upgrade.
_DEFAULT_ENABLED_LOCALES = '["da", "en", "fr"]'


def upgrade() -> None:
    op.add_column(
        'app_settings',
        sa.Column(
            'enabled_locales',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=_DEFAULT_ENABLED_LOCALES,
        ),
    )
    op.alter_column('app_settings', 'enabled_locales', server_default=None)


def downgrade() -> None:
    op.drop_column('app_settings', 'enabled_locales')

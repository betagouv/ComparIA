"""add_default_locale

Revision ID: f8c2b6a41d70
Revises: e3a7c5f19b04
Create Date: 2026-07-21 00:00:00.000000

"""
import os
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel

# revision identifiers, used by Alembic.
revision: str = 'f8c2b6a41d70'
down_revision: Union[str, Sequence[str], None] = 'e3a7c5f19b04'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Frozen copy of SUPPORTED_LOCALES at the time of this revision. Migrations don't
# import app code, so this list stays right even after the model's list moves on.
_SUPPORTED_LOCALES = ('da', 'en', 'fr', 'lt', 'sv')


def _instance_locale() -> str:
    # The da instance used to get its locale from the frontend's DEFAULT_LOCALE
    # env var, which this column replaces. Seed from the backend's own instance
    # name so ai-arenaen.dk doesn't come back up in French after the upgrade.
    portal = os.environ.get('DEFAULT_COUNTRY_PORTAL', 'fr')
    return portal if portal in _SUPPORTED_LOCALES else 'fr'


def upgrade() -> None:
    op.add_column(
        'app_settings',
        sa.Column(
            'default_locale',
            sqlmodel.sql.sqltypes.AutoString(),
            nullable=False,
            server_default=_instance_locale(),
        ),
    )
    op.alter_column('app_settings', 'default_locale', server_default=None)


def downgrade() -> None:
    op.drop_column('app_settings', 'default_locale')

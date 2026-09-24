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

# Frozen copy of DEFAULT_ENABLED_LOCALES at the time of this revision. Migrations
# don't import app code, so this stays right even after the model's list moves on.
# It is the enabled set rather than the supported one, so the value seeded here is
# always part of the enabled_locales the previous revision wrote.
_DEFAULT_ENABLED_LOCALES = ('da', 'en', 'fr')


def _instance_locale() -> str:
    # The da instance used to get its locale from the frontend's DEFAULT_LOCALE
    # env var, which this column replaces. Seed from the backend's own instance
    # name so ai-arenaen.dk doesn't come back up in French after the upgrade.
    #
    # Refuse to guess when the variable is absent: defaulting to fr here is
    # exactly how the da database would quietly end up in French. Raising rolls
    # the whole upgrade back, since env.py wraps the run in one transaction.
    portal = os.environ.get('COMPARIA_INSTANCE_NAME', '').strip()
    if not portal:
        raise RuntimeError(
            'COMPARIA_INSTANCE_NAME must be set to run this migration, so the '
            "instance's own locale is seeded rather than guessed."
        )
    # A portal that isn't a locale code (a museum or private instance) is a
    # deliberate case rather than a mistake: those run in French.
    return portal if portal in _DEFAULT_ENABLED_LOCALES else 'fr'


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

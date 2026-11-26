"""widen_locale_columns

Revision ID: b6d1e8f3a2c5
Revises: f2a9c7e1d4b6
Create Date: 2026-11-12 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'b6d1e8f3a2c5'
down_revision: Union[str, Sequence[str], None] = 'f2a9c7e1d4b6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Locales are checked against SUPPORTED_LOCALES in the models, the columns no
# longer cap their length. suggestion_category.locale was VARCHAR(2), too short
# for nb-NO.
_COLUMNS = (
    ('suggestion_category', 'locale', 2),
    ('auth_consent_log', 'language', 16),
    ('anonymous_consent_log', 'language', 16),
)


def upgrade() -> None:
    for table, column, length in _COLUMNS:
        op.alter_column(
            table,
            column,
            type_=sa.String(),
            existing_type=sa.String(length=length),
        )


def downgrade() -> None:
    for table, column, length in _COLUMNS:
        op.alter_column(
            table,
            column,
            type_=sa.String(length=length),
            existing_type=sa.String(),
        )

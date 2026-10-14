"""add_arena_limits_to_app_settings

Revision ID: 4414aec5a67e
Revises: 84f4becbdc4c
Create Date: 2026-10-14 15:36:53.595060

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4414aec5a67e'
down_revision: Union[str, Sequence[str], None] = '84f4becbdc4c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_LIMITS = (
    'limit_all_per_session',
    'limit_all_per_ip',
    'limit_expensive_per_session',
    'limit_expensive_per_ip',
    'limit_expected_answer_chars',
)


def upgrade() -> None:
    # Empty everywhere: an instance keeps its RATELIMIT_* defaults until an
    # admin sets its own.
    for name in _LIMITS:
        op.add_column('app_settings', sa.Column(name, sa.Integer(), nullable=True))
    op.add_column(
        'app_settings', sa.Column('limits_updated_at', sa.DateTime(), nullable=True)
    )
    op.add_column(
        'app_settings', sa.Column('limits_updated_by', sa.Uuid(), nullable=True)
    )
    op.create_foreign_key(
        'fk_app_settings_limits_updated_by_auth_user',
        'app_settings',
        'auth_user',
        ['limits_updated_by'],
        ['id'],
    )


def downgrade() -> None:
    op.drop_constraint(
        'fk_app_settings_limits_updated_by_auth_user',
        'app_settings',
        type_='foreignkey',
    )
    op.drop_column('app_settings', 'limits_updated_by')
    op.drop_column('app_settings', 'limits_updated_at')
    for name in reversed(_LIMITS):
        op.drop_column('app_settings', name)

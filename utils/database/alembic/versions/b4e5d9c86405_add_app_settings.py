"""add_app_settings

Revision ID: b4e5d9c86405
Revises: d078b1411db3
Create Date: 2026-07-10 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'b4e5d9c86405'
down_revision: Union[str, Sequence[str], None] = 'd078b1411db3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'app_settings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('auth_access_policy', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('auth_domain_allowlist', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('votes_objective', sa.Integer(), nullable=False),
        sa.Column('updated_at', postgresql.TIMESTAMP(), nullable=False),
        sa.Column('updated_by', sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(['updated_by'], ['auth_user.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.execute(
        "INSERT INTO app_settings (id, auth_access_policy, auth_domain_allowlist, votes_objective, updated_at) "
        "VALUES (1, 'anonymous_first', '[]', 300000, now())"
    )


def downgrade() -> None:
    op.drop_table('app_settings')

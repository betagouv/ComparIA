"""add_auth_invite_token

Revision ID: d078b1411db3
Revises: f7f638e57c03
Create Date: 2026-07-08 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'd078b1411db3'
down_revision: Union[str, Sequence[str], None] = 'f7f638e57c03'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'auth_invite_token',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('invited_by', sa.Uuid(), nullable=False),
        sa.Column('token_hash', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('created_at', postgresql.TIMESTAMP(), nullable=False),
        sa.Column('expires_at', postgresql.TIMESTAMP(), nullable=False),
        sa.Column('used_at', postgresql.TIMESTAMP(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['auth_user.id']),
        sa.ForeignKeyConstraint(['invited_by'], ['auth_user.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_auth_invite_token_token_hash', 'auth_invite_token', ['token_hash'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_auth_invite_token_token_hash', table_name='auth_invite_token')
    op.drop_table('auth_invite_token')

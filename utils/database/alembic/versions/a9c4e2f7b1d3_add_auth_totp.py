"""add_auth_totp

Revision ID: a9c4e2f7b1d3
Revises: 269a5fc3959c
Create Date: 2026-09-14 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a9c4e2f7b1d3'
down_revision: Union[str, Sequence[str], None] = '269a5fc3959c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'auth_totp',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('secret_encrypted', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('confirmed_at', postgresql.TIMESTAMP(), nullable=True),
        sa.Column('pending_secret_encrypted', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('pending_created_at', postgresql.TIMESTAMP(), nullable=True),
        sa.Column('last_used_step', sa.Integer(), nullable=True),
        sa.Column('created_at', postgresql.TIMESTAMP(), nullable=False),
        sa.Column('updated_at', postgresql.TIMESTAMP(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['auth_user.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id'),
    )
    op.create_table(
        'auth_totp_challenge',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('token_hash', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('created_at', postgresql.TIMESTAMP(), nullable=False),
        sa.Column('expires_at', postgresql.TIMESTAMP(), nullable=False),
        sa.Column('used_at', postgresql.TIMESTAMP(), nullable=True),
        sa.Column('attempts', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['auth_user.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_auth_totp_challenge_token_hash', 'auth_totp_challenge', ['token_hash'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_auth_totp_challenge_token_hash', table_name='auth_totp_challenge')
    op.drop_table('auth_totp_challenge')
    op.drop_table('auth_totp')

"""add_auth_tables

Revision ID: b2d4a7e9c1f3
Revises: 89de92001a7e
Create Date: 2026-06-17 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'b2d4a7e9c1f3'
down_revision: Union[str, Sequence[str], None] = '83c86b798214'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'auth_user',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('email', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('created_at', postgresql.TIMESTAMP(), nullable=False),
        sa.Column('last_seen_at', postgresql.TIMESTAMP(), nullable=False),
        sa.Column('deleted_at', postgresql.TIMESTAMP(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
    )
    op.create_table(
        'auth_login_code',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('code_hash', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('created_at', postgresql.TIMESTAMP(), nullable=False),
        sa.Column('expires_at', postgresql.TIMESTAMP(), nullable=False),
        sa.Column('used_at', postgresql.TIMESTAMP(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['auth_user.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table(
        'auth_session',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('token_hash', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('created_at', postgresql.TIMESTAMP(), nullable=False),
        sa.Column('expires_at', postgresql.TIMESTAMP(), nullable=False),
        sa.Column('revoked_at', postgresql.TIMESTAMP(), nullable=True),
        sa.Column('user_agent', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('ip', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['auth_user.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_auth_session_token_hash', 'auth_session', ['token_hash'], unique=False)
    op.create_table(
        'auth_consent_log',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('terms_version', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('consented_at', postgresql.TIMESTAMP(), nullable=False),
        sa.Column('ip', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['auth_user.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.add_column('comparison', sa.Column('user_id', sa.Uuid(), nullable=True))
    op.create_foreign_key(
        'fk_comparison_user_id', 'comparison', 'auth_user', ['user_id'], ['id']
    )


def downgrade() -> None:
    op.drop_constraint('fk_comparison_user_id', 'comparison', type_='foreignkey')
    op.drop_column('comparison', 'user_id')
    op.drop_table('auth_consent_log')
    op.drop_index('ix_auth_session_token_hash', table_name='auth_session')
    op.drop_table('auth_session')
    op.drop_table('auth_login_code')
    op.drop_table('auth_user')

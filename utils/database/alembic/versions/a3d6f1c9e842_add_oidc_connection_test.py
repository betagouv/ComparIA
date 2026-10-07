"""add_oidc_connection_test

Revision ID: a3d6f1c9e842
Revises: 7e2b9d4c1a68
Create Date: 2026-09-30 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a3d6f1c9e842'
down_revision: Union[str, Sequence[str], None] = '7e2b9d4c1a68'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'app_settings',
        sa.Column(
            'oidc_connection_test',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column('app_settings', 'oidc_connection_test')

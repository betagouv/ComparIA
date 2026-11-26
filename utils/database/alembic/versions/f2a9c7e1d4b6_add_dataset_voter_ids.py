"""add_dataset_voter_ids

Revision ID: f2a9c7e1d4b6
Revises: e3b7d9a2c4f1
Create Date: 2026-11-04 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'f2a9c7e1d4b6'
down_revision: Union[str, Sequence[str], None] = 'e3b7d9a2c4f1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Off on every instance until an admin turns it on. The key is made by the
    # first build that needs it.
    op.add_column(
        'app_settings',
        sa.Column(
            'dataset_voter_ids', sa.Boolean(), nullable=False, server_default='false'
        ),
    )
    op.alter_column('app_settings', 'dataset_voter_ids', server_default=None)
    op.add_column(
        'app_settings',
        sa.Column('dataset_voter_key_encrypted', sa.LargeBinary(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('app_settings', 'dataset_voter_key_encrypted')
    op.drop_column('app_settings', 'dataset_voter_ids')

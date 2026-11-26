"""add publish_sending

Revision ID: 60128c026929
Revises: 0e1680903d6f
Create Date: 2026-10-26 16:44:30.416532

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '60128c026929'
down_revision: Union[str, Sequence[str], None] = '0e1680903d6f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'publish_sending',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('created_at', postgresql.TIMESTAMP(), nullable=False),
        sa.Column('updated_at', postgresql.TIMESTAMP(), nullable=False),
        sa.Column('dataset', sa.String(), nullable=False),
        sa.Column('started_at', postgresql.TIMESTAMP(), nullable=False),
        sa.Column('sent_until', postgresql.TIMESTAMP(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_publish_sending_dataset', 'publish_sending', ['dataset'], unique=False
    )
    # A destination that ran before this table existed may have sent anything
    # created until now: its last start is too early, a run that was building
    # then still picked up newer comparisons.
    op.execute(
        """
        INSERT INTO publish_sending
            (id, created_at, updated_at, dataset, started_at, sent_until)
        SELECT gen_random_uuid(), now(), now(), dataset,
            timezone('utc', now()), timezone('utc', now())
        FROM publish_destination,
            jsonb_array_elements_text(datasets) AS dataset
        WHERE last_run_started_at IS NOT NULL
        """
    )


def downgrade() -> None:
    op.drop_index('ix_publish_sending_dataset', table_name='publish_sending')
    op.drop_table('publish_sending')

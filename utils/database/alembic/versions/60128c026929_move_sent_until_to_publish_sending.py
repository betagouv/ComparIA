"""move sent_until to publish_sending

Revision ID: 60128c026929
Revises: 0043c215df64
Create Date: 2026-10-26 16:44:30.416532

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '60128c026929'
down_revision: Union[str, Sequence[str], None] = '0043c215df64'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Deleting a destination, or changing what it receives, forgot what it had
    # sent. The history now lives apart from the destinations.
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
    op.execute(
        """
        INSERT INTO publish_sending
            (id, created_at, updated_at, dataset, started_at, sent_until)
        SELECT gen_random_uuid(), now(), now(), dataset, sent_until, sent_until
        FROM publish_destination,
            jsonb_array_elements_text(datasets) AS dataset
        WHERE sent_until IS NOT NULL
        """
    )
    op.drop_column('publish_destination', 'sent_until')


def downgrade() -> None:
    op.add_column(
        'publish_destination',
        sa.Column('sent_until', postgresql.TIMESTAMP(), nullable=True),
    )
    # Which destination sent what is lost going back: give each the latest
    # date, which blocks more rather than less.
    op.execute(
        """
        UPDATE publish_destination
        SET sent_until = (SELECT max(sent_until) FROM publish_sending)
        """
    )
    op.drop_index('ix_publish_sending_dataset', table_name='publish_sending')
    op.drop_table('publish_sending')

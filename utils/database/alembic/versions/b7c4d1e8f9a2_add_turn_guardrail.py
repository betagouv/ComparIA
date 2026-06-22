"""add Turn 'guardrail'

Revision ID: b7c4d1e8f9a2
Revises: 89de92001a7e
Create Date: 2026-06-22 10:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'b7c4d1e8f9a2'
down_revision: Union[str, Sequence[str], None] = '89de92001a7e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('turn', sa.Column('guardrail', postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('turn', 'guardrail')

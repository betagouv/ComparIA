"""add_daily_usd_cap_to_llm_data

Revision ID: 8db1ac83a809
Revises: 4414aec5a67e
Create Date: 2026-10-14 20:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8db1ac83a809'
down_revision: Union[str, Sequence[str], None] = '4414aec5a67e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Empty everywhere: no model is capped until an admin sets one.
    op.add_column('llm_data', sa.Column('daily_usd_cap', sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column('llm_data', 'daily_usd_cap')

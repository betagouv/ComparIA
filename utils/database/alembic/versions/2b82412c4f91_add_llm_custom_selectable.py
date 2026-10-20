"""add LLMData 'custom_selectable'

Revision ID: 2b82412c4f91
Revises: c4e8a2f1b9d3
Create Date: 2026-10-20 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '2b82412c4f91'
down_revision: Union[str, Sequence[str], None] = 'c4e8a2f1b9d3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'llm_data',
        sa.Column(
            'custom_selectable', sa.Boolean(), nullable=False, server_default=sa.true()
        ),
    )


def downgrade() -> None:
    op.drop_column('llm_data', 'custom_selectable')

"""add_cost_weight_to_llm_data

Revision ID: 7181adf67155
Revises: c4e8a2f1b9d3
Create Date: 2026-10-13 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '7181adf67155'
down_revision: Union[str, Sequence[str], None] = 'c4e8a2f1b9d3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# What a model with today's `rate_limited` costs, until an admin sets each
# model's own weight.
RATE_LIMITED_WEIGHT = 4


def upgrade() -> None:
    op.add_column(
        'llm_data',
        sa.Column('cost_weight', sa.Float(), nullable=False, server_default='1'),
    )
    op.execute(
        sa.text(
            'UPDATE llm_data SET cost_weight = :weight WHERE rate_limited'
        ).bindparams(weight=RATE_LIMITED_WEIGHT)
    )
    # rate_limited stays until the code that reads it is gone everywhere:
    # the pods still running during the upgrade read and write it. The new
    # code leaves it out of its inserts, so it needs a default. A later
    # migration drops it.
    op.alter_column('llm_data', 'rate_limited', server_default=sa.false())


def downgrade() -> None:
    op.execute('UPDATE llm_data SET rate_limited = cost_weight > 1')
    op.alter_column('llm_data', 'rate_limited', server_default=None)
    op.drop_column('llm_data', 'cost_weight')

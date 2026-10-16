"""stop_reading_rate_limited

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


def upgrade() -> None:
    # A model's prices now say whether it is expensive, so the model no longer
    # reads rate_limited. The column stays until the code that reads it is
    # gone everywhere: the pods still running during the upgrade read and
    # write it. The new code leaves it out of its inserts, so it needs a
    # default. A later migration drops it.
    op.alter_column('llm_data', 'rate_limited', server_default=sa.false())


def downgrade() -> None:
    # The flags set before the upgrade are still there; a model added since
    # comes back not rate limited.
    op.alter_column('llm_data', 'rate_limited', server_default=None)

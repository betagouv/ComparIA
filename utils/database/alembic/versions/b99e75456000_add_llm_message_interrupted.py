"""add llm_message interrupted

Revision ID: b99e75456000
Revises: 269a5fc3959c
Create Date: 2026-09-15 16:20:17.000106

"""

from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b99e75456000"
down_revision: Union[str, Sequence[str], None] = "269a5fc3959c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Every existing answer ran to its end: only answers the user stops from
    # now on carry the flag.
    op.add_column(
        "llm_message",
        sa.Column(
            "interrupted", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("llm_message", "interrupted")

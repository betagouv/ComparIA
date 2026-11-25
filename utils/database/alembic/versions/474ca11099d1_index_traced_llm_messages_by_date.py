"""index traced llm messages by date

Revision ID: 474ca11099d1
Revises: 65aa45f5e710
Create Date: 2026-11-25 13:07:12.257158

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "474ca11099d1"
down_revision: Union[str, Sequence[str], None] = "65aa45f5e710"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # The admin tools list counts tool calls over the last 30 days. Without
    # this, each visit reads the whole llm_message table. Built concurrently
    # so the arena keeps writing messages while it is made.
    with op.get_context().autocommit_block():
        op.create_index(
            "ix_llm_message_traced_created_at",
            "llm_message",
            ["created_at"],
            unique=False,
            postgresql_where=sa.text("jsonb_typeof(agent_trace) = 'array'"),
            postgresql_concurrently=True,
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.get_context().autocommit_block():
        op.drop_index(
            "ix_llm_message_traced_created_at",
            table_name="llm_message",
            postgresql_concurrently=True,
        )

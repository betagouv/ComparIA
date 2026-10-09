"""index traced llm messages by date

Revision ID: a375433e6a93
Revises: f81103805a8d
Create Date: 2026-10-08 15:30:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a375433e6a93"
down_revision: Union[str, Sequence[str], None] = "f81103805a8d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
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
    with op.get_context().autocommit_block():
        op.drop_index(
            "ix_llm_message_traced_created_at",
            table_name="llm_message",
            postgresql_concurrently=True,
        )

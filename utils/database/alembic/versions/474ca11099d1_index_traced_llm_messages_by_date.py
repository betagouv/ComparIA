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


INDEX_NAME = "ix_llm_message_traced_created_at"


def upgrade() -> None:
    """Upgrade schema."""
    # The admin tools list counts tool calls over the last 30 days. Without
    # this, each visit reads the whole llm_message table. Built concurrently
    # so the arena keeps writing messages while it is made.
    #
    # The build commits on its own, outside the migration transaction: a run
    # that fails later leaves the index behind, and one killed during the
    # build leaves it invalid. Rerunning keeps a valid one, rebuilds an
    # invalid one.
    with op.get_context().autocommit_block():
        valid = (
            op.get_bind()
            .execute(
                sa.text(
                    "SELECT i.indisvalid FROM pg_index i"
                    " JOIN pg_class c ON c.oid = i.indexrelid"
                    " WHERE c.relname = :name"
                ),
                {"name": INDEX_NAME},
            )
            .scalar()
        )
        if valid:
            return
        if valid is not None:
            op.drop_index(
                INDEX_NAME, table_name="llm_message", postgresql_concurrently=True
            )
        op.create_index(
            INDEX_NAME,
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
            INDEX_NAME,
            table_name="llm_message",
            postgresql_concurrently=True,
        )

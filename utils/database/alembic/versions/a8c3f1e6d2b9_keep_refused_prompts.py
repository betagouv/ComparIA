"""keep refused prompts

A message the prompt check refused, or warned about without the person
sending it, never becomes a turn, so its text was lost: the admin saw a count
and nothing to read. Its result now keeps the text, and the conversation it
was meant for when it was a follow-up. Deleting the conversation deletes it.
The retention rule on prompt_check_result already purges it.

Revision ID: a8c3f1e6d2b9
Revises: d7e2a9c4b1f8
Create Date: 2026-10-23 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a8c3f1e6d2b9"
down_revision: Union[str, Sequence[str], None] = "d7e2a9c4b1f8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# What the activity panel lists: the messages a check stopped or warned about.
STOPPED = (
    "decision IN ('warned', 'blocked') OR (decision = 'error' AND message IS NOT NULL)"
)


def upgrade() -> None:
    op.add_column(
        "prompt_check_result",
        sa.Column("prompt", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    )
    op.add_column(
        "prompt_check_result",
        sa.Column("comparison_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "prompt_check_result_comparison_id_fkey",
        "prompt_check_result",
        "comparison",
        ["comparison_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(
        "ix_prompt_check_result_stopped",
        "prompt_check_result",
        ["created_at", "id"],
        postgresql_where=sa.text(STOPPED),
    )
    op.create_index(
        "ix_prompt_check_result_comparison_id",
        "prompt_check_result",
        ["comparison_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_prompt_check_result_comparison_id", table_name="prompt_check_result"
    )
    op.drop_index("ix_prompt_check_result_stopped", table_name="prompt_check_result")
    op.drop_constraint(
        "prompt_check_result_comparison_id_fkey",
        "prompt_check_result",
        type_="foreignkey",
    )
    op.drop_column("prompt_check_result", "comparison_id")
    op.drop_column("prompt_check_result", "prompt")

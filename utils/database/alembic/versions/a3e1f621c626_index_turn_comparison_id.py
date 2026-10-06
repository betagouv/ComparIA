"""index turn.comparison_id

Revision ID: a3e1f621c626
Revises: 58abc2a23978
Create Date: 2026-10-06 09:00:00.000000

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a3e1f621c626"
down_revision: Union[str, Sequence[str], None] = "58abc2a23978"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Deleting a comparison makes Postgres look for turns that still point
    # at it. Without this index, each one is a full read of the turn table.
    with op.get_context().autocommit_block():
        op.create_index(
            "ix_turn_comparison_id",
            "turn",
            ["comparison_id"],
            unique=False,
            postgresql_concurrently=True,
        )


def downgrade() -> None:
    with op.get_context().autocommit_block():
        op.drop_index(
            "ix_turn_comparison_id",
            table_name="turn",
            postgresql_concurrently=True,
        )

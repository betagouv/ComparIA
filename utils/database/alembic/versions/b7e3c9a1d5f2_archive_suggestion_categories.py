"""archive_suggestion_categories

Revision ID: b7e3c9a1d5f2
Revises: a6c2e9f4b1d8
Create Date: 2026-08-24 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b7e3c9a1d5f2"
down_revision: str | Sequence[str] | None = "a6c2e9f4b1d8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "suggestion_category",
        sa.Column("archived_at", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "suggestion_category",
        sa.Column("archived_by", sa.Uuid(), nullable=True),
    )
    op.create_index(
        op.f("ix_suggestion_category_archived_at"),
        "suggestion_category",
        ["archived_at"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_suggestion_category_archived_by_auth_user",
        "suggestion_category",
        "auth_user",
        ["archived_by"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_suggestion_category_archived_by_auth_user",
        "suggestion_category",
        type_="foreignkey",
    )
    op.drop_index(
        op.f("ix_suggestion_category_archived_at"),
        table_name="suggestion_category",
    )
    op.drop_column("suggestion_category", "archived_by")
    op.drop_column("suggestion_category", "archived_at")

"""add_admin_activity_indexes

Revision ID: 7e2a4c9d1b6f
Revises: 5c8bd69940b5
Create Date: 2026-10-05 00:00:00.000000

"""

import logging
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7e2a4c9d1b6f"
down_revision: Union[str, Sequence[str], None] = "5c8bd69940b5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

logger = logging.getLogger("alembic.runtime.migration")


def upgrade() -> None:
    with op.get_context().autocommit_block():
        # Every join from a comparison to its turns. Missing until now: the
        # arena only ever reached turns through the comparison's relationship.
        op.create_index(
            "ix_turn_comparison_id",
            "turn",
            ["comparison_id"],
            unique=False,
            postgresql_concurrently=True,
        )
        # The activity list pages on (created_at, id), archived rows included
        # when asked, which the statistics index leaves out.
        op.create_index(
            "ix_comparison_created_at_id",
            "comparison",
            ["created_at", "id"],
            unique=False,
            postgresql_concurrently=True,
        )
        op.create_index(
            "ix_comparison_categories",
            "comparison",
            ["categories"],
            unique=False,
            postgresql_using="gin",
            postgresql_ops={"categories": "jsonb_path_ops"},
            postgresql_concurrently=True,
        )

        # Prompt search. pg_trgm ships with Postgres, but a managed database
        # can refuse to create an extension: the search then still works,
        # by reading every prompt of the period, so do not fail the deploy.
        op.execute(sa.text("""
                DO $$
                BEGIN
                    CREATE EXTENSION IF NOT EXISTS pg_trgm;
                EXCEPTION WHEN OTHERS THEN
                    RAISE WARNING 'pg_trgm unavailable: %', SQLERRM;
                END
                $$
                """))
        has_trgm = (
            op.get_bind()
            .execute(sa.text("SELECT 1 FROM pg_extension WHERE extname = 'pg_trgm'"))
            .first()
        )
        if has_trgm:
            op.create_index(
                "ix_user_message_content_trgm",
                "user_message",
                ["content"],
                unique=False,
                postgresql_using="gin",
                postgresql_ops={"content": "gin_trgm_ops"},
                postgresql_concurrently=True,
            )
        else:
            logger.warning(
                "pg_trgm is not available: prompt search in the admin will"
                " work without an index"
            )


def downgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute(
            sa.text("DROP INDEX CONCURRENTLY IF EXISTS ix_user_message_content_trgm")
        )
        for name, table in (
            ("ix_comparison_categories", "comparison"),
            ("ix_comparison_created_at_id", "comparison"),
            ("ix_turn_comparison_id", "turn"),
        ):
            op.drop_index(name, table_name=table, postgresql_concurrently=True)

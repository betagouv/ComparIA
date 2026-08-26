"""date-only LLM metadata and durable USD exchange rates

Revision ID: d2b7f4a9c6e1
Revises: c1a6e8f2d4b7
Create Date: 2026-08-26 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d2b7f4a9c6e1"
down_revision: Union[str, Sequence[str], None] = "c1a6e8f2d4b7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "llm_data",
        "release_date",
        existing_type=sa.DateTime(),
        type_=sa.Date(),
        existing_nullable=False,
        postgresql_using="release_date::date",
    )
    op.alter_column(
        "llm_data",
        "knowledge_cutoff",
        existing_type=sa.DateTime(),
        type_=sa.Date(),
        existing_nullable=True,
        postgresql_using="knowledge_cutoff::date",
    )
    op.create_table(
        "exchange_rate",
        sa.Column("currency_code", sa.String(length=3), nullable=False),
        sa.Column("rate_from_usd", sa.Float(), nullable=False),
        sa.Column("rate_date", sa.Date(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("currency_code"),
    )


def downgrade() -> None:
    op.drop_table("exchange_rate")
    op.alter_column(
        "llm_data",
        "knowledge_cutoff",
        existing_type=sa.Date(),
        type_=sa.DateTime(),
        existing_nullable=True,
        postgresql_using="knowledge_cutoff::timestamp",
    )
    op.alter_column(
        "llm_data",
        "release_date",
        existing_type=sa.Date(),
        type_=sa.DateTime(),
        existing_nullable=False,
        postgresql_using="release_date::timestamp",
    )

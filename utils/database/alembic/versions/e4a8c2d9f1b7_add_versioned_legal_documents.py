"""add versioned legal documents

Revision ID: e4a8c2d9f1b7
Revises: c6a1f3e8d2b7
Create Date: 2026-07-24 00:00:00.000000

"""

import hashlib
import uuid
from datetime import datetime, timezone
from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "e4a8c2d9f1b7"
down_revision: Union[str, Sequence[str], None] = "c6a1f3e8d2b7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "legal_document",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("kind", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("version", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("language", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("content", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column(
            "content_hash", sqlmodel.sql.sqltypes.AutoString(length=64), nullable=False
        ),
        sa.Column("published_at", postgresql.TIMESTAMP(), nullable=False),
        sa.Column("effective_at", postgresql.TIMESTAMP(), nullable=False),
        sa.Column("retired_at", postgresql.TIMESTAMP(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "kind", "version", "language", name="uq_legal_document_version"
        ),
    )
    op.create_index(
        op.f("ix_legal_document_content_hash"),
        "legal_document",
        ["content_hash"],
        unique=False,
    )
    op.add_column(
        "app_settings",
        sa.Column("legal_presentation", postgresql.JSONB(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("app_settings", "legal_presentation")
    op.drop_index(op.f("ix_legal_document_content_hash"), table_name="legal_document")
    op.drop_table("legal_document")

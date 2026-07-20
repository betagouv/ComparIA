"""add versioned legal documents and auditable consent

Revision ID: e4a8c2d9f1b7
Revises: c6a1f3e8d2b7
Create Date: 2026-07-20 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel
from alembic import op
from sqlalchemy.dialects import postgresql

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
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_hash", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("published_at", postgresql.TIMESTAMP(), nullable=False),
        sa.Column("effective_at", postgresql.TIMESTAMP(), nullable=False),
        sa.Column("retired_at", postgresql.TIMESTAMP(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("kind", "version", "language", name="uq_legal_document_version"),
    )
    op.create_index(
        "ix_legal_document_content_hash", "legal_document", ["content_hash"], unique=False
    )
    op.add_column("auth_consent_log", sa.Column("document_id", sa.Uuid(), nullable=True))
    op.add_column(
        "auth_consent_log",
        sa.Column("document_hash", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    )
    op.add_column(
        "auth_consent_log",
        sa.Column("language", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    )
    op.add_column(
        "auth_consent_log",
        sa.Column(
            "purpose",
            sqlmodel.sql.sqltypes.AutoString(),
            nullable=False,
            server_default="terms_and_participation",
        ),
    )
    op.add_column(
        "auth_consent_log",
        sa.Column("client_accepted_at", postgresql.TIMESTAMP(), nullable=True),
    )
    op.add_column(
        "auth_consent_log",
        sa.Column("withdrawn_at", postgresql.TIMESTAMP(), nullable=True),
    )
    op.create_foreign_key(
        "fk_auth_consent_log_document_id",
        "auth_consent_log",
        "legal_document",
        ["document_id"],
        ["id"],
    )
    op.create_table(
        "anonymous_consent_log",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("anonymous_user_hash", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("terms_version", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("document_hash", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("language", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("purpose", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("client_accepted_at", postgresql.TIMESTAMP(), nullable=False),
        sa.Column("consented_at", postgresql.TIMESTAMP(), nullable=False),
        sa.Column("withdrawn_at", postgresql.TIMESTAMP(), nullable=True),
        sa.ForeignKeyConstraint(["document_id"], ["legal_document.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_anonymous_consent_log_anonymous_user_hash",
        "anonymous_consent_log",
        ["anonymous_user_hash"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_anonymous_consent_log_anonymous_user_hash",
        table_name="anonymous_consent_log",
    )
    op.drop_table("anonymous_consent_log")
    op.drop_constraint(
        "fk_auth_consent_log_document_id", "auth_consent_log", type_="foreignkey"
    )
    for column in (
        "withdrawn_at",
        "client_accepted_at",
        "purpose",
        "language",
        "document_hash",
        "document_id",
    ):
        op.drop_column("auth_consent_log", column)
    op.drop_index("ix_legal_document_content_hash", table_name="legal_document")
    op.drop_table("legal_document")

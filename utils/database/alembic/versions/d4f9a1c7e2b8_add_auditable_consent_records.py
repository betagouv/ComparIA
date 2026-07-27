"""add auditable consent records

Revision ID: d4f9a1c7e2b8
Revises: e4a8c2d9f1b7
Create Date: 2026-07-27 10:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "d4f9a1c7e2b8"
down_revision: Union[str, Sequence[str], None] = "e4a8c2d9f1b7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "anonymous_consent_log",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "anonymous_user_hash",
            sqlmodel.sql.sqltypes.AutoString(length=64),
            nullable=False,
        ),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("terms_version", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column(
            "document_hash",
            sqlmodel.sql.sqltypes.AutoString(length=64),
            nullable=False,
        ),
        sa.Column(
            "language", sqlmodel.sql.sqltypes.AutoString(length=16), nullable=False
        ),
        sa.Column("purpose", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("client_accepted_at", postgresql.TIMESTAMP(), nullable=False),
        sa.Column("consented_at", postgresql.TIMESTAMP(), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["legal_document.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_anonymous_consent_log_anonymous_user_hash"),
        "anonymous_consent_log",
        ["anonymous_user_hash"],
        unique=False,
    )

    op.add_column(
        "auth_consent_log", sa.Column("document_id", sa.Uuid(), nullable=True)
    )
    op.add_column(
        "auth_consent_log",
        sa.Column(
            "document_hash",
            sqlmodel.sql.sqltypes.AutoString(length=64),
            nullable=True,
        ),
    )
    op.add_column(
        "auth_consent_log", sa.Column("auth_session_id", sa.Uuid(), nullable=True)
    )
    op.add_column(
        "auth_consent_log",
        sa.Column("source_anonymous_consent_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "auth_consent_log",
        sa.Column(
            "language", sqlmodel.sql.sqltypes.AutoString(length=16), nullable=True
        ),
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
        sa.Column("associated_at", postgresql.TIMESTAMP(), nullable=True),
    )
    op.create_foreign_key(
        "fk_auth_consent_log_document_id",
        "auth_consent_log",
        "legal_document",
        ["document_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_auth_consent_log_auth_session_id",
        "auth_consent_log",
        "auth_session",
        ["auth_session_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_auth_consent_log_source_anonymous",
        "auth_consent_log",
        "anonymous_consent_log",
        ["source_anonymous_consent_id"],
        ["id"],
    )
    op.create_unique_constraint(
        "uq_auth_consent_log_source_anonymous",
        "auth_consent_log",
        ["user_id", "source_anonymous_consent_id"],
    )
    op.create_index(
        "ix_auth_consent_log_user_id_consented_at",
        "auth_consent_log",
        ["user_id", sa.text("consented_at DESC")],
        unique=False,
    )

    op.add_column(
        "comparison",
        sa.Column(
            "participation_terms_version",
            sqlmodel.sql.sqltypes.AutoString(),
            nullable=True,
            server_default="legacy-pre-versioning",
        ),
    )
    # Attribute past comparisons to the consent that was in force when they were
    # created. Comparisons with no matching consent keep the legacy marker
    # rather than borrowing a version they never saw.
    op.execute(sa.text("""
            UPDATE comparison AS comparison_row
            SET participation_terms_version = CONCAT(
                'legacy-',
                (
                  SELECT consent.terms_version
                  FROM auth_consent_log AS consent
                  WHERE consent.user_id = comparison_row.user_id
                    AND consent.consented_at <= comparison_row.created_at
                  ORDER BY consent.consented_at DESC
                  LIMIT 1
                )
            )
            WHERE comparison_row.user_id IS NOT NULL
              AND EXISTS (
                  SELECT 1
                  FROM auth_consent_log AS consent
                  WHERE consent.user_id = comparison_row.user_id
                    AND consent.consented_at <= comparison_row.created_at
              )
            """))
    op.alter_column("comparison", "participation_terms_version", nullable=False)


def downgrade() -> None:
    op.drop_column("comparison", "participation_terms_version")
    op.drop_index(
        "ix_auth_consent_log_user_id_consented_at", table_name="auth_consent_log"
    )
    op.drop_constraint(
        "uq_auth_consent_log_source_anonymous", "auth_consent_log", type_="unique"
    )
    op.drop_constraint(
        "fk_auth_consent_log_source_anonymous", "auth_consent_log", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_auth_consent_log_auth_session_id", "auth_consent_log", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_auth_consent_log_document_id", "auth_consent_log", type_="foreignkey"
    )
    for column in (
        "associated_at",
        "client_accepted_at",
        "purpose",
        "language",
        "source_anonymous_consent_id",
        "auth_session_id",
        "document_hash",
        "document_id",
    ):
        op.drop_column("auth_consent_log", column)
    op.drop_index(
        op.f("ix_anonymous_consent_log_anonymous_user_hash"),
        table_name="anonymous_consent_log",
    )
    op.drop_table("anonymous_consent_log")

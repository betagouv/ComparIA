"""add consent association provenance

Revision ID: f7b2d4a9c6e1
Revises: e4a8c2d9f1b7
Create Date: 2026-07-20 14:45:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "f7b2d4a9c6e1"
down_revision: Union[str, Sequence[str], None] = "e4a8c2d9f1b7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "auth_consent_log", sa.Column("auth_session_id", sa.Uuid(), nullable=True)
    )
    op.add_column(
        "auth_consent_log",
        sa.Column("source_anonymous_consent_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "auth_consent_log",
        sa.Column("associated_at", postgresql.TIMESTAMP(), nullable=True),
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


def downgrade() -> None:
    op.drop_constraint(
        "uq_auth_consent_log_source_anonymous",
        "auth_consent_log",
        type_="unique",
    )
    op.drop_constraint(
        "fk_auth_consent_log_source_anonymous",
        "auth_consent_log",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_auth_consent_log_auth_session_id",
        "auth_consent_log",
        type_="foreignkey",
    )
    op.drop_column("auth_consent_log", "associated_at")
    op.drop_column("auth_consent_log", "source_anonymous_consent_id")
    op.drop_column("auth_consent_log", "auth_session_id")

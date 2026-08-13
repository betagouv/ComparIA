"""add_oidc_config_to_app_settings

Revision ID: a1b2c3d4e5f6
Revises: f8c2b6a41d70
Create Date: 2026-08-12 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "f8c2b6a41d70"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_DEFAULT_AUTH_METHODS = '["email_code"]'
_DEFAULT_OIDC_SCOPES = '["openid", "email"]'


def upgrade() -> None:
    op.add_column(
        "app_settings",
        sa.Column(
            "auth_methods",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=_DEFAULT_AUTH_METHODS,
        ),
    )
    op.alter_column("app_settings", "auth_methods", server_default=None)

    op.add_column(
        "app_settings",
        sa.Column("oidc_issuer", sa.String(), nullable=True),
    )
    op.add_column(
        "app_settings",
        sa.Column("oidc_client_id", sa.String(), nullable=True),
    )
    op.add_column(
        "app_settings",
        sa.Column("oidc_client_secret_encrypted", sa.LargeBinary(), nullable=True),
    )
    op.add_column(
        "app_settings",
        sa.Column(
            "oidc_scopes",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=_DEFAULT_OIDC_SCOPES,
        ),
    )
    op.alter_column("app_settings", "oidc_scopes", server_default=None)

    op.add_column(
        "app_settings",
        sa.Column("oidc_button_label", sa.String(), nullable=True),
    )
    op.add_column(
        "app_settings",
        sa.Column("oidc_button_logo", sa.LargeBinary(), nullable=True),
    )
    op.add_column(
        "app_settings",
        sa.Column("oidc_button_logo_content_type", sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("app_settings", "oidc_button_logo_content_type")
    op.drop_column("app_settings", "oidc_button_logo")
    op.drop_column("app_settings", "oidc_button_label")
    op.drop_column("app_settings", "oidc_scopes")
    op.drop_column("app_settings", "oidc_client_secret_encrypted")
    op.drop_column("app_settings", "oidc_client_id")
    op.drop_column("app_settings", "oidc_issuer")
    op.drop_column("app_settings", "auth_methods")

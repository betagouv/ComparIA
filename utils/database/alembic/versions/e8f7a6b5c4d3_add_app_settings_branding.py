"""add_app_settings_branding

Revision ID: e8f7a6b5c4d3
Revises: e4f5a6b7c8d9
Create Date: 2026-07-27 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel

# revision identifiers, used by Alembic.
revision: str = "e8f7a6b5c4d3"
down_revision: Union[str, Sequence[str], None] = "e4f5a6b7c8d9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    for column_name, default in (
        ("primary_color_light", "#6464F3"),
        ("primary_color_dark", "#9898F8"),
        ("secondary_color_light", "#FF9575"),
        ("secondary_color_dark", "#FFCC00"),
    ):
        op.add_column(
            "app_settings",
            sa.Column(
                column_name,
                sqlmodel.sql.sqltypes.AutoString(length=7),
                nullable=False,
                server_default=default,
            ),
        )
        op.alter_column("app_settings", column_name, server_default=None)
    op.add_column(
        "app_settings",
        sa.Column(
            "homepage_url",
            sqlmodel.sql.sqltypes.AutoString(length=2048),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("app_settings", "homepage_url")
    op.drop_column("app_settings", "secondary_color_dark")
    op.drop_column("app_settings", "secondary_color_light")
    op.drop_column("app_settings", "primary_color_dark")
    op.drop_column("app_settings", "primary_color_light")

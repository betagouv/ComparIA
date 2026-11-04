"""add_app_settings_home_texts

Revision ID: c5e2a9d7f413
Revises: a8c3f1e6d2b9
Create Date: 2026-10-29 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "c5e2a9d7f413"
down_revision: Union[str, Sequence[str], None] = "a8c3f1e6d2b9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    for column_name in ("home_title", "home_prompt_placeholder", "home_banner"):
        op.add_column(
            "app_settings",
            sa.Column(
                column_name,
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
                server_default="{}",
            ),
        )
        op.alter_column("app_settings", column_name, server_default=None)


def downgrade() -> None:
    op.drop_column("app_settings", "home_banner")
    op.drop_column("app_settings", "home_prompt_placeholder")
    op.drop_column("app_settings", "home_title")

"""add_analysis_model_settings

Revision ID: d7b3e6a1c852
Revises: c9a2f5b7d3e1
Create Date: 2026-08-03 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d7b3e6a1c852"
down_revision: Union[str, Sequence[str], None] = "c9a2f5b7d3e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# What llm_analyze.py asked for before this setting existed, through the
# OpenRouter endpoint every instance already has.
_MODEL = "google/gemini-3.1-flash-lite-preview"
_OPENROUTER_ENDPOINT_ID = "9667ee84-9b07-4d3d-890c-57fc9ffe9c33"


def upgrade() -> None:
    op.add_column(
        "app_settings", sa.Column("analysis_endpoint_id", sa.Uuid(), nullable=True)
    )
    op.add_column(
        "app_settings",
        sa.Column("analysis_model", sa.String(length=200), nullable=True),
    )
    op.create_foreign_key(
        "fk_app_settings_analysis_endpoint_id_llm_endpoint",
        "app_settings",
        "llm_endpoint",
        ["analysis_endpoint_id"],
        ["id"],
    )

    # Point the analysis at the model it already used, so an instance that
    # analyses comparisons today goes on analysing them. An operator can change
    # it in the admin panel afterwards, which is the point of the setting.
    op.execute(
        sa.text(
            """
            UPDATE app_settings
               SET analysis_endpoint_id = :endpoint_id,
                   analysis_model = :model
             WHERE analysis_endpoint_id IS NULL
               AND EXISTS (SELECT 1 FROM llm_endpoint WHERE id = :endpoint_id)
            """
        ).bindparams(
            sa.bindparam("endpoint_id", _OPENROUTER_ENDPOINT_ID, type_=sa.Uuid()),
            sa.bindparam("model", _MODEL, type_=sa.String()),
        )
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_app_settings_analysis_endpoint_id_llm_endpoint",
        "app_settings",
        type_="foreignkey",
    )
    op.drop_column("app_settings", "analysis_model")
    op.drop_column("app_settings", "analysis_endpoint_id")

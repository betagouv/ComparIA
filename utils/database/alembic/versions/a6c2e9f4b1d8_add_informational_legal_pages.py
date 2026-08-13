"""add informational legal pages

Revision ID: a6c2e9f4b1d8
Revises: f4a8c2d9e1b7
Create Date: 2026-08-11 00:00:00.000000
"""

import json
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a6c2e9f4b1d8"
down_revision: Union[str, Sequence[str], None] = "f4a8c2d9e1b7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Frozen seed: migrations must not import mutable application defaults.
SEEDED_INFORMATIONAL_LEGAL_PAGES = {
    "legal_notice": {
        "mode": "internal",
        "external_url": None,
        "visible_in_legal_menu": True,
        "visible_in_settings": True,
        "content_by_locale": {},
    },
    "accessibility": {
        "mode": "internal",
        "external_url": None,
        "visible_in_legal_menu": True,
        "visible_in_settings": True,
        "content_by_locale": {},
    },
    "ecodesign": {
        "mode": "internal",
        "external_url": None,
        "visible_in_legal_menu": True,
        "visible_in_settings": True,
        "content_by_locale": {},
    },
}


def upgrade() -> None:
    seed = json.dumps(SEEDED_INFORMATIONAL_LEGAL_PAGES)
    op.add_column(
        "app_settings",
        sa.Column(
            "informational_legal_pages",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text(f"'{seed}'::jsonb"),
        ),
    )
    op.alter_column("app_settings", "informational_legal_pages", server_default=None)


def downgrade() -> None:
    op.drop_column("app_settings", "informational_legal_pages")

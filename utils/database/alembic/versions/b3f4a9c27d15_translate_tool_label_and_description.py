"""translate tool label and description

Revision ID: b3f4a9c27d15
Revises: 60128c026929
Create Date: 2026-11-26 17:05:00.000000

"""

import re
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "b3f4a9c27d15"
down_revision: Union[str, Sequence[str], None] = "60128c026929"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _default_locale() -> str:
    """The language the existing names were written in: the instance's default
    one. Without settings yet, French, the language the seeded tools use."""
    locale = (
        op.get_bind()
        .execute(sa.text("SELECT default_locale FROM app_settings LIMIT 1"))
        .scalar()
    )
    locale = locale or "fr"
    # Inlined below: a cast's USING clause takes no bound parameter.
    if not re.fullmatch(r"[a-z]{2,3}(-[A-Za-z]{2,4})?", locale):
        raise ValueError(f"Unexpected default locale {locale!r}")
    return locale


def upgrade() -> None:
    """Upgrade schema."""
    locale = _default_locale()
    op.alter_column(
        "tool",
        "label",
        type_=postgresql.JSONB(astext_type=sa.Text()),
        postgresql_using=f"jsonb_build_object('{locale}', label)",
        existing_nullable=False,
    )
    op.alter_column(
        "tool",
        "description",
        type_=postgresql.JSONB(astext_type=sa.Text()),
        postgresql_using=(
            "CASE WHEN coalesce(description, '') = '' THEN NULL"
            f" ELSE jsonb_build_object('{locale}', description) END"
        ),
        existing_nullable=True,
    )


def downgrade() -> None:
    """Downgrade schema."""
    locale = _default_locale()
    # The default language's text, else French or English.
    op.alter_column(
        "tool",
        "label",
        type_=sa.String(),
        postgresql_using=f"coalesce(label->>'{locale}', label->>'fr', label->>'en')",
        existing_nullable=False,
    )
    op.alter_column(
        "tool",
        "description",
        type_=sa.String(),
        postgresql_using=(
            f"coalesce(description->>'{locale}', description->>'fr',"
            " description->>'en')"
        ),
        existing_nullable=True,
    )

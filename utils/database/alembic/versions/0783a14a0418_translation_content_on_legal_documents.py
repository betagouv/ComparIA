"""translation content on legal documents

Revision ID: 0783a14a0418
Revises: 67fb732c509e
Create Date: 2026-10-25 21:21:01.364929

"""

from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0783a14a0418"
down_revision: Union[str, Sequence[str], None] = "67fb732c509e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()

    documents = sa.table(
        "legal_document",
        sa.column("id", sa.Uuid()),
        sa.column("kind", sa.String()),
        sa.column("version", sa.String()),
        sa.column("language", sa.String()),
        sa.column("content", sa.Text()),
        sa.column("content_json", sa.JSON()),
    )

    # Add a temporary JSON column while the existing content is still text.
    op.add_column(
        "legal_document",
        sa.Column("content_json", sa.JSON(), nullable=True),
    )

    rows = (
        bind.execute(
            sa.select(
                documents.c.id,
                documents.c.kind,
                documents.c.version,
                documents.c.language,
                documents.c.content,
            )
        )
        .mappings()
        .all()
    )

    grouped = {}
    for row in rows:
        key = (row["kind"], row["version"])
        grouped.setdefault(key, []).append(row)

    for group in grouped.values():
        # Keep one row and combine all its translations into that row.
        keep = group[0]
        translations = {row["language"]: row["content"] for row in group}

        bind.execute(
            sa.update(documents)
            .where(documents.c.id == keep["id"])
            .values(content_json=translations)
        )

        duplicate_ids = [row["id"] for row in group[1:]]
        if duplicate_ids:
            bind.execute(sa.delete(documents).where(documents.c.id.in_(duplicate_ids)))

    op.drop_constraint(
        "uq_legal_document_version",
        "legal_document",
        type_="unique",
    )
    op.drop_column("legal_document", "content")
    op.drop_column("legal_document", "language")
    op.alter_column(
        "legal_document",
        "content_json",
        new_column_name="content",
        existing_type=sa.JSON(),
        nullable=False,
    )

    op.create_unique_constraint(
        "uq_legal_document_version",
        "legal_document",
        ["kind", "version"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()

    documents = sa.table(
        "legal_document",
        sa.column("id", sa.Uuid()),
        sa.column("content", sa.JSON()),
    )

    rows = bind.execute(sa.select(documents.c.id, documents.c.content)).mappings().all()

    op.drop_constraint(
        "uq_legal_document_version",
        "legal_document",
        type_="unique",
    )
    op.add_column(
        "legal_document",
        sa.Column("language", sa.String(), nullable=True),
    )
    op.add_column(
        "legal_document",
        sa.Column("content_text", sa.Text(), nullable=True),
    )

    for row in rows:
        locale = next(
            (locale for locale in set(row["content"]) if row["content"].get(locale)),
            None,
        )
        if locale is None:
            raise ValueError(f"no content for legal document '{row['id']}'")
        else:
            bind.execute(
                sa.update(documents)
                .where(documents.c.id == row["id"])
                .values(language=locale, content_text=row["content"][locale])
            )

    op.drop_column("legal_document", "content")
    op.alter_column(
        "legal_document",
        "content_text",
        new_column_name="content",
        existing_type=sa.Text(),
        nullable=False,
    )
    op.alter_column("legal_document", "language", nullable=False)

    op.create_unique_constraint(
        "uq_legal_document_version",
        "legal_document",
        ["kind", "version", "language"],
    )

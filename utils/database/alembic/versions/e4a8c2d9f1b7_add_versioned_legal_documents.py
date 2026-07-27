"""add versioned legal documents

Revision ID: e4a8c2d9f1b7
Revises: c6a1f3e8d2b7
Create Date: 2026-07-24 00:00:00.000000

"""

import hashlib
import uuid
from datetime import datetime, timezone
from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "e4a8c2d9f1b7"
down_revision: Union[str, Sequence[str], None] = "c6a1f3e8d2b7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Starter terms so a fresh install is never blocked on an unpublished document.
SEED_ID = uuid.UUID("6f1b6f6e-8f4a-4c3e-9a2f-2d0d5a1f7b41")
SEED_VERSION = "0-initiale-a-remplacer"
SEED_CONTENT = """# Conditions générales d’utilisation

Version initiale, à remplacer par l’éditeur de la plateforme depuis
l’administration. Elle décrit seulement ce que la plateforme fait aujourd’hui.

## Objet

Compar:IA permet de comparer les réponses de plusieurs modèles d’IA à une même
question, puis de voter pour celle que vous préférez.

## Vos messages

Les messages que vous saisissez sont transmis aux fournisseurs des modèles
comparés pour produire les réponses. Ne saisissez aucune donnée sensible ni
aucune information permettant d’identifier une personne.

## Réutilisation des conversations

Les conversations et les votes sont conservés et peuvent être réutilisés pour
évaluer les modèles, pour la recherche et pour la publication de jeux de
données ouverts.

## Évolution

Une nouvelle version de ces conditions peut être publiée à tout moment. La
version applicable est celle affichée sur cette page.
"""


def upgrade() -> None:
    op.create_table(
        "legal_document",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("kind", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("version", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("language", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("content", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column(
            "content_hash", sqlmodel.sql.sqltypes.AutoString(length=64), nullable=False
        ),
        sa.Column("published_at", postgresql.TIMESTAMP(), nullable=False),
        sa.Column("effective_at", postgresql.TIMESTAMP(), nullable=False),
        sa.Column("retired_at", postgresql.TIMESTAMP(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "kind", "version", "language", name="uq_legal_document_version"
        ),
    )
    op.create_index(
        op.f("ix_legal_document_content_hash"),
        "legal_document",
        ["content_hash"],
        unique=False,
    )
    op.add_column(
        "app_settings",
        sa.Column("legal_presentation", postgresql.JSONB(), nullable=True),
    )

    # Every legal timestamp is naive UTC.
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    op.bulk_insert(
        sa.table(
            "legal_document",
            sa.column("id", sa.Uuid()),
            sa.column("kind", sa.String()),
            sa.column("version", sa.String()),
            sa.column("language", sa.String()),
            sa.column("content", sa.String()),
            sa.column("content_hash", sa.String()),
            sa.column("published_at", postgresql.TIMESTAMP()),
            sa.column("effective_at", postgresql.TIMESTAMP()),
        ),
        [
            {
                "id": SEED_ID,
                "kind": "terms",
                "version": SEED_VERSION,
                "language": "fr",
                "content": SEED_CONTENT,
                "content_hash": hashlib.sha256(
                    SEED_CONTENT.encode("utf-8")
                ).hexdigest(),
                "published_at": now,
                "effective_at": now,
            }
        ],
    )


def downgrade() -> None:
    op.drop_column("app_settings", "legal_presentation")
    op.drop_index(op.f("ix_legal_document_content_hash"), table_name="legal_document")
    op.drop_table("legal_document")

"""add selection modes, llm tags and the arena tools switch

Revision ID: da69fc86f2ea
Revises: a375433e6a93
Create Date: 2026-11-12 00:00:00.000000

Downgrade drops the table and the two LLM columns but leaves comparisons
alone: one stored under a mode created since keeps that key, which the old
code, typing `mode` as the four built-in keys, does not expect. Rewriting
them would lose what they were drawn under, so it is left to whoever
downgrades.
"""

import uuid
from datetime import datetime
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "da69fc86f2ea"
down_revision: Union[str, Sequence[str], None] = "a375433e6a93"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# The four modes that used to be hard-coded, with the same keys, so every
# stored comparison still names a live mode and draws do not change on
# upgrade. Labels are the 'modes.<key>' messages of the locale files as they
# were when the modes moved here, frozen: a migration must not read files.
# Only supported locales: 'et.json' has them too but 'et' cannot be stored.
_TEXTS = {
    "random": {
        "label": {
            "da": "Tilfældig",
            "en": "Random",
            "fr": "Aléatoire",
            "it": "Casuale",
            "nb-NO": "Tilfeldig",
            "sv": "Slump",
        },
        "short_label": {
            "da": "Vilkårligt modelvalg",
            "en": "Random model selection",
            "fr": "Modèles aléatoires",
            "it": "Modelli casuali",
            "nb-NO": "Tilfeldig valg av modeller",
            "sv": "Slumpmässigt val av modeller",
        },
        "description": {
            "da": "To modeller valgt vilkårligt fra den fulde liste",
            "en": "Two models chosen randomly from the full list",
            "fr": "Deux modèles choisis au hasard parmi toute la liste",
            "it": "Due modelli scelti a caso dall'intera lista",
            "nb-NO": "To modeller valgt tilfeldig fra hele listen",
            "sv": "Två modeller utvalda slumpmässigt från hela listan",
        },
    },
    "small-models": {
        "label": {
            "da": "Sparsom",
            "en": "Frugal",
            "fr": "Frugal",
            "it": "Frugale",
            "nb-NO": "Ressurssparende",
            "sv": "Sparsam",
        },
        "short_label": {
            "da": "Sparsom modeludvælgelse",
            "en": "Frugal model selection",
            "fr": "Modèles frugaux",
            "it": "Modelli frugali",
            "nb-NO": "Valg av ressurssparende modeller",
            "sv": "Sparsamma modeller",
        },
        "description": {
            "da": "To små modeller valgt tilfældigt",
            "en": "Two small models chosen randomly",
            "fr": "Deux modèles tirés au hasard parmi ceux de plus petite taille",
            "it": "Due modelli scelti a caso tra i più piccoli",
            "nb-NO": "To tilfeldig valgte små modeller",
            "sv": "Två slumpmässigt valda modeller, ur kategorin små modeller",
        },
    },
    "big-vs-small": {
        "label": {
            "da": "David mod Goliat",
            "en": "David vs Goliath",
            "fr": "David contre Goliath",
            "it": "Davide contro Golia",
            "nb-NO": "David mot Goliat",
            "sv": "David mot Goliat",
        },
        "short_label": {
            "da": "David mod Goliat-modelvalg",
            "en": "David vs Goliath model selection",
            "fr": "David contre Goliath",
            "it": "Davide contro Golia",
            "nb-NO": "David mot Goliat-modellutvalg",
            "sv": "David mot Goliat",
        },
        "description": {
            "da": "En lille model mod en stor model, begge valgt tilfældigt",
            "en": "One small model against one big model, both chosen randomly",
            "fr": "Un petit modèle contre un grand, les deux tirés au hasard",
            "it": "Un modello piccolo contro uno grande, entrambi scelti a caso",
            "nb-NO": "En liten modell mot en stor modell, begge valgt tilfeldig",
            "sv": "En liten modell mot en stor, båda valda slumpmässigt",
        },
    },
    "custom": {
        "label": {
            "da": "Manuel udvælgelse",
            "en": "Manual selection",
            "fr": "Sélection manuelle",
            "it": "Selezione manuale",
            "nb-NO": "Manuelt valg",
            "sv": "Manuellt val",
        },
        "short_label": {
            "da": "Manuel modeludvælgelse",
            "en": "Manual model selection",
            "fr": "Sélection manuelle",
            "it": "Selezione manuale",
            "nb-NO": "Manuelt valg av modeller",
            "sv": "Manuellt val",
        },
        "description": {
            "da": "Kan du genkende de to modeller, du valgte?",
            "en": "Will you recognize the two models you chose?",
            "fr": "Reconnaîtrez-vous les deux modèles que vous avez choisis ?",
            "it": "Riusciresti a riconoscere i due modelli che hai scelto?",
            "nb-NO": "Vil du kjenne igjen de to modellene du har valgt?",
            "sv": "Kommer du att känna igen de två modellerna du valde?",
        },
    },
}

# (key, icon, visitor_picks, pool_a, pool_b). The thresholds are the old
# SMALL_MODELS_BUCKET_UPPER_LIMIT (60) and BIG_MODELS_BUCKET_LOWER_LIMIT (100).
_MODES = [
    ("random", "i-ri-dice-line", 0, {}, None),
    ("small-models", "i-ri-leaf-line", 0, {"params_max": 60}, None),
    ("big-vs-small", "i-ri-ruler-line", 0, {"params_min": 100}, {"params_max": 60}),
    ("custom", "i-ri-search-line", 2, {}, None),
]
_SEED_TIMESTAMP = datetime(2026, 11, 12)
_SEED_NAMESPACE = uuid.UUID("3b8f2c1e-5d4a-4f6b-9e7c-1a2b3c4d5e6f")


def upgrade() -> None:
    # Off for a system that brings its own retrieval or tools: it is then
    # called without the arena's. Every existing model keeps getting them.
    op.add_column(
        "llm_data",
        sa.Column(
            "arena_tools", sa.Boolean(), server_default=sa.true(), nullable=False
        ),
    )
    op.add_column(
        "llm_data",
        sa.Column(
            "tags",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="[]",
            nullable=False,
        ),
    )

    selection_mode = op.create_table(
        "selection_mode",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", postgresql.TIMESTAMP(), nullable=False),
        sa.Column("updated_at", postgresql.TIMESTAMP(), nullable=False),
        sa.Column("key", sa.String(), nullable=False),
        sa.Column("label", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "short_label", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column(
            "description", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("icon", sa.String(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False),
        sa.Column("visitor_picks", sa.Integer(), nullable=False),
        sa.Column("pool_a", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("pool_b", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("pairing", sa.String(), nullable=False),
        sa.Column("sampling", sa.String(), nullable=False),
        sa.Column("tools_policy", sa.String(), nullable=False),
        sa.Column("tool_keys", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("cohorts", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("locales", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("starts_at", postgresql.TIMESTAMP(), nullable=True),
        sa.Column("ends_at", postgresql.TIMESTAMP(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_selection_mode_key"), "selection_mode", ["key"], unique=True
    )
    # One default at most, even when two admins save at once.
    op.create_index(
        "ix_selection_mode_one_default",
        "selection_mode",
        ["is_default"],
        unique=True,
        postgresql_where=sa.text("is_default"),
    )

    op.bulk_insert(
        selection_mode,
        [
            {
                "id": uuid.uuid5(_SEED_NAMESPACE, key),
                "created_at": _SEED_TIMESTAMP,
                "updated_at": _SEED_TIMESTAMP,
                "key": key,
                **_TEXTS[key],
                "icon": icon,
                "enabled": True,
                "position": position,
                "is_default": key == "random",
                "visitor_picks": visitor_picks,
                "pool_a": pool_a,
                "pool_b": pool_b,
                "pairing": "any",
                "sampling": "uniform",
                "tools_policy": "visitor",
                "tool_keys": [],
                "cohorts": [],
                "locales": [],
                "starts_at": None,
                "ends_at": None,
            }
            for position, (key, icon, visitor_picks, pool_a, pool_b) in enumerate(
                _MODES
            )
        ],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_selection_mode_one_default",
        table_name="selection_mode",
        postgresql_where=sa.text("is_default"),
    )
    op.drop_index(op.f("ix_selection_mode_key"), table_name="selection_mode")
    op.drop_table("selection_mode")
    op.drop_column("llm_data", "tags")
    op.drop_column("llm_data", "arena_tools")

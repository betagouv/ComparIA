"""add_voice_input

Creates the voice_settings singleton and the voice_recording table behind it:
a microphone in the prompt box, transcribed by a speech model drawn at random
from an admin-editable pool.

Revision ID: a1c9e4d70b52
Revises: c24f368ecff0
Create Date: 2026-08-07 00:00:00.000000

"""

from datetime import datetime
from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "a1c9e4d70b52"
down_revision: Union[str, Sequence[str], None] = "c24f368ecff0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# A frozen copy of DEFAULT_MODELS. Migrations do not import app code: the pool
# will drift as models are retired, and this row records what was seeded on the
# day, not what the constant says now.
SEEDED_MODELS = [
    "mistralai/voxtral-mini-transcribe",
    "nvidia/parakeet-tdt-0.6b-v3",
    "openai/gpt-4o-mini-transcribe",
    "deepgram/nova-3",
]


def upgrade() -> None:
    voice_settings = op.create_table(
        "voice_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "store_audio", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column("models", postgresql.JSONB(), nullable=False),
        sa.Column("endpoint_id", sa.Uuid(), nullable=True),
        sa.Column("max_seconds", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("retention_days", sa.Integer(), nullable=True),
        sa.Column("updated_at", postgresql.TIMESTAMP(), nullable=False),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(
            ["endpoint_id"], ["llm_endpoint.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["updated_by"], ["auth_user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # Seeded off. An instance opts into recording voices, it does not discover
    # one day that it has been keeping them.
    op.bulk_insert(
        voice_settings,
        [
            {
                "id": 1,
                "enabled": False,
                "store_audio": False,
                "models": SEEDED_MODELS,
                "max_seconds": 60,
                "updated_at": datetime.now(),
            }
        ],
    )

    op.create_table(
        "voice_recording",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", postgresql.TIMESTAMP(), nullable=False),
        sa.Column("turn_id", sa.Uuid(), nullable=True),
        sa.Column("audio", sa.LargeBinary(), nullable=False),
        sa.Column("content_type", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.Column("model", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("transcription", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("locale", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["turn_id"], ["turn.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_voice_recording_turn_id", "voice_recording", ["turn_id"])


def downgrade() -> None:
    op.drop_index("ix_voice_recording_turn_id", table_name="voice_recording")
    op.drop_table("voice_recording")
    op.drop_table("voice_settings")

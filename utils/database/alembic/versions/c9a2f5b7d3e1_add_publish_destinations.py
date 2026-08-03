"""add_publish_destinations

Revision ID: c9a2f5b7d3e1
Revises: e8f7a6b5c4d3
Create Date: 2026-08-03 00:00:00.000000

"""

import os
import uuid
from datetime import datetime
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "c9a2f5b7d3e1"
down_revision: Union[str, Sequence[str], None] = "e8f7a6b5c4d3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    destination_table = op.create_table(
        "publish_destination",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", postgresql.TIMESTAMP(), nullable=False),
        sa.Column("updated_at", postgresql.TIMESTAMP(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("datasets", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # An instance already publishing keeps publishing: its two environment
    # variables become the destination it would otherwise have to retype. They
    # are read nowhere else after this migration.
    repo_path = os.environ.get("HF_PUSH_DATASET_PATH", "").strip()
    token = os.environ.get("HF_PUSH_DATASET_KEY", "").strip()
    if repo_path.count("/") == 1 and all(repo_path.split("/")) and token:
        now = datetime.now()
        op.bulk_insert(
            destination_table,
            [
                {
                    "id": uuid.uuid4(),
                    "created_at": now,
                    "updated_at": now,
                    "name": "Hugging Face",
                    "kind": "huggingface",
                    "config": {
                        "kind": "huggingface",
                        "repo_path": repo_path,
                        "token": token,
                    },
                    "datasets": ["normal", "raw"],
                    "enabled": True,
                }
            ],
        )


def downgrade() -> None:
    op.drop_table("publish_destination")

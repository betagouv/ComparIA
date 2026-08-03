"""add_vote_tags

Revision ID: b3d1c7a4e9f2
Revises: e8f7a6b5c4d3
Create Date: 2026-08-03 00:00:00.000000

"""

import uuid
from datetime import datetime
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "b3d1c7a4e9f2"
down_revision: Union[str, Sequence[str], None] = "e8f7a6b5c4d3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# The tags that used to be two Literal unions in backend/config.py. They are
# seeded as reserved rows: every instance keeps them, keeps these keys, and
# keeps them out of the labels column because they are translated in the
# message files. Emoji are the ones the frontend used to hardcode.
_SEED = [
    ("useful", "positive", "🙌"),
    ("complete", "positive", "💯"),
    ("creative", "positive", "🌀"),
    ("clear_formatting", "positive", "🎨"),
    ("incorrect", "negative", "❌"),
    ("superficial", "negative", "🚩"),
    ("instructions_not_followed", "negative", "🚫"),
]
_SEED_TIMESTAMP = datetime(2026, 8, 3)
_SEED_NAMESPACE = uuid.UUID("6f6f9a0c-6b2e-4d5e-9f1f-2c3f4a5b6c7d")


def upgrade() -> None:
    vote_tag_table = op.create_table(
        "vote_tag",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", postgresql.TIMESTAMP(), nullable=False),
        sa.Column("updated_at", postgresql.TIMESTAMP(), nullable=False),
        sa.Column("key", sa.String(length=100), nullable=False),
        sa.Column("sign", sa.String(), nullable=False),
        sa.Column("emoji", sa.String(length=16), nullable=False),
        sa.Column("reserved", sa.Boolean(), nullable=False),
        sa.Column("labels", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("display_order", sa.Integer(), nullable=False),
        sa.Column("archived_at", postgresql.TIMESTAMP(), nullable=True),
        sa.Column("archived_by", sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(["archived_by"], ["auth_user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_vote_tag_key"), "vote_tag", ["key"], unique=True)
    op.create_index(
        op.f("ix_vote_tag_archived_at"), "vote_tag", ["archived_at"], unique=False
    )

    order = {"positive": 0, "negative": 0}
    rows = []
    for key, sign, emoji in _SEED:
        rows.append(
            {
                "id": uuid.uuid5(_SEED_NAMESPACE, key),
                "created_at": _SEED_TIMESTAMP,
                "updated_at": _SEED_TIMESTAMP,
                "key": key,
                "sign": sign,
                "emoji": emoji,
                "reserved": True,
                "display_order": order[sign],
                "archived_at": None,
                "archived_by": None,
            }
        )
        order[sign] += 1
    op.bulk_insert(vote_tag_table, rows)


def downgrade() -> None:
    op.drop_index(op.f("ix_vote_tag_archived_at"), table_name="vote_tag")
    op.drop_index(op.f("ix_vote_tag_key"), table_name="vote_tag")
    op.drop_table("vote_tag")

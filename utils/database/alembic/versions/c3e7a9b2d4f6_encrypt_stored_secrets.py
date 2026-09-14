"""encrypt_stored_secrets

Revision ID: c3e7a9b2d4f6
Revises: a9c4e2f7b1d3
Create Date: 2026-09-14 00:00:00.000000

Rewrites the provider API keys, the moderation key and the publishing
credentials as Fernet tokens under COMPARIA_ENCRYPTION_KEY. No schema
change: the columns keep their type, only their content changes. A value
that already looks like a token is left alone, so the migration can be
re-run on a half-migrated database.

"""

import json
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from utils.database.encrypted import looks_encrypted
from utils.database.models.publish import SECRET_FIELDS
from utils.secrets import decrypt_secret, encrypt_secret

# revision identifiers, used by Alembic.
revision: str = "c3e7a9b2d4f6"
down_revision: Union[str, Sequence[str], None] = "a9c4e2f7b1d3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_STRING_COLUMNS = (("llm_endpoint", "api_key"), ("prompt_check", "api_key"))


def _rewrite_strings(transform, skip) -> None:
    connection = op.get_bind()
    for table, column in _STRING_COLUMNS:
        rows = connection.execute(
            sa.text(f"SELECT id, {column} FROM {table} WHERE {column} IS NOT NULL")
        ).all()
        for row_id, value in rows:
            if not value or skip(value):
                continue
            connection.execute(
                sa.text(f"UPDATE {table} SET {column} = :value WHERE id = :id"),
                {"value": transform(value), "id": row_id},
            )


def _rewrite_configs(transform, skip) -> None:
    connection = op.get_bind()
    rows = connection.execute(
        sa.text("SELECT id, config FROM publish_destination")
    ).all()
    for row_id, config in rows:
        if isinstance(config, str):
            config = json.loads(config)
        changed = dict(config)
        for field in SECRET_FIELDS.get(changed.get("kind"), ()):
            value = changed.get(field)
            if value and not skip(value):
                changed[field] = transform(value)
        if changed != config:
            connection.execute(
                sa.text(
                    "UPDATE publish_destination SET config = CAST(:config AS jsonb) "
                    "WHERE id = :id"
                ),
                {"config": json.dumps(changed), "id": row_id},
            )


def _decrypt(value: str) -> str:
    plain = decrypt_secret(value)
    if plain is None:
        raise RuntimeError(
            "a stored secret cannot be decrypted with COMPARIA_ENCRYPTION_KEY; "
            "put the key it was written with back in the list before downgrading"
        )
    return plain


def upgrade() -> None:
    _rewrite_strings(encrypt_secret, looks_encrypted)
    _rewrite_configs(encrypt_secret, looks_encrypted)


def downgrade() -> None:
    _rewrite_strings(_decrypt, lambda value: not looks_encrypted(value))
    _rewrite_configs(_decrypt, lambda value: not looks_encrypted(value))

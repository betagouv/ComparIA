"""Which stored secrets the configured keys open.

Shared by the backend's startup check and the key rotation command: both
load every secret-bearing row and look for a token no key in
COMPARIA_ENCRYPTION_KEY decrypts. Nothing here writes.
"""

import logging
from dataclasses import dataclass
from typing import Any

from sqlmodel import select

from utils.database.encrypted import UnreadableSecret
from utils.database.models.auth import UserTotp
from utils.database.models.llms.endpoint import LLMEndpoint
from utils.database.models.prompt_check import PromptCheck
from utils.database.models.publish import SECRET_FIELDS, PublishDestination
from utils.database.session import get_session
from utils.secrets import SecretUnreadableError, decrypt_secret

logger = logging.getLogger("comparia.db")

# The columns an encrypted type decodes on load.
ENCRYPTED_COLUMNS: tuple[tuple[type, str], ...] = (
    (LLMEndpoint, "api_key"),
    (PromptCheck, "api_key"),
    (PublishDestination, "config"),
)
# The authenticator secrets hold their tokens explicitly, decoded by hand.
TOTP_COLUMNS = ("secret_encrypted", "pending_secret_encrypted")


@dataclass(frozen=True)
class UnreadableRow:
    table: str
    row_id: Any
    column: str

    def __str__(self) -> str:
        return f"{self.table} {self.row_id}.{self.column}"


async def load_secret_rows(session: Any, lock: bool = False) -> dict[type, list]:
    """Every row that holds a secret, by model. Locked when the caller means
    to rewrite them, so a save from the admin panel waits for the whole run
    rather than being overwritten by what was read before it."""
    rows: dict[type, list] = {}
    for model in (*(model for model, _ in ENCRYPTED_COLUMNS), UserTotp):
        statement = select(model)
        if lock:
            statement = statement.with_for_update()
        rows[model] = (await session.exec(statement)).all()
    return rows


def unreadable_secrets(rows: dict[type, list]) -> list[UnreadableRow]:
    """The secrets of the loaded rows that no configured key opens, one
    entry per row and column. Never the values."""
    found: list[UnreadableRow] = []
    for model, column in ENCRYPTED_COLUMNS:
        for row in rows.get(model, ()):
            value = getattr(row, column)
            if isinstance(value, UnreadableSecret):
                found.append(UnreadableRow(model.__tablename__, row.id, column))
            elif isinstance(value, dict):
                for field in SECRET_FIELDS.get(value.get("kind"), ()):
                    if isinstance(value.get(field), UnreadableSecret):
                        found.append(
                            UnreadableRow(
                                model.__tablename__, row.id, f"{column}.{field}"
                            )
                        )
    for totp in rows.get(UserTotp, ()):
        for column in TOTP_COLUMNS:
            token = getattr(totp, column)
            if not token:
                continue
            try:
                decrypt_secret(token)
            except SecretUnreadableError:
                found.append(UnreadableRow(UserTotp.__tablename__, totp.id, column))
    return found


async def log_unreadable_secrets() -> list[UnreadableRow]:
    """Startup check: one error per stored secret the configured keys do not
    open, naming the row. Nothing is changed and nothing is raised: an
    endpoint whose key went missing is disabled by its own reader, the rest
    of the arena keeps running."""
    async with get_session() as session:
        unreadable = unreadable_secrets(await load_secret_rows(session))
    for ref in unreadable:
        logger.error(
            f"[SECRETS] {ref} cannot be decrypted with COMPARIA_ENCRYPTION_KEY: "
            "put the key it was written with back in the list"
        )
    return unreadable

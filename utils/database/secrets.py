"""Which stored secrets the configured keys open.

Shared by the backend's startup check and the key rotation command: both
load every secret-bearing row and look for a token no key in
COMPARIA_ENCRYPTION_KEY decrypts. Nothing here writes.
"""

import logging
from typing import Any

from sqlmodel import select

from utils.database.encrypted import UnreadableRow, UnreadableSecret
from utils.database.models.app_settings import AppSettings
from utils.database.models.auth import UserTotp
from utils.database.models.llms.endpoint import LLMEndpoint
from utils.database.models.prompt_check import PromptCheck
from utils.database.models.publish import PublishDestination
from utils.database.session import get_session
from utils.secrets import can_decrypt

logger = logging.getLogger("comparia.db")

# The columns an encrypted type decodes on load.
ENCRYPTED_COLUMNS: tuple[tuple[type, str], ...] = (
    (LLMEndpoint, "api_key"),
    (PromptCheck, "api_key"),
    (PublishDestination, "config"),
)
# The columns that hold their tokens explicitly, decoded by hand: the
# authenticator secrets as text, the OIDC client secret as bytes.
TOKEN_COLUMNS: tuple[tuple[type, str], ...] = (
    (UserTotp, "secret_encrypted"),
    (UserTotp, "pending_secret_encrypted"),
    (AppSettings, "oidc_client_secret_encrypted"),
)


def token_text(token: str | bytes) -> str:
    """The token a column holds, as text."""
    return token.decode() if isinstance(token, bytes) else token


async def load_secret_rows(session: Any, lock: bool = False) -> dict[type, list]:
    """Every row that holds a secret, by model. Locked when the caller means
    to rewrite them, so a save from the admin panel waits for the whole run
    rather than being overwritten by what was read before it."""
    rows: dict[type, list] = {}
    models = dict.fromkeys(model for model, _ in (*ENCRYPTED_COLUMNS, *TOKEN_COLUMNS))
    for model in models:
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
            elif isinstance(row, PublishDestination):
                for field in row.unreadable_fields():
                    found.append(
                        UnreadableRow(model.__tablename__, row.id, f"{column}.{field}")
                    )
    for model, column in TOKEN_COLUMNS:
        for row in rows.get(model, ()):
            token = getattr(row, column)
            if token and not can_decrypt(token_text(token)):
                found.append(UnreadableRow(model.__tablename__, row.id, column))
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
            f"[SECRETS] {ref.message()}: "
            "put the key it was written with back in the list"
        )
    return unreadable

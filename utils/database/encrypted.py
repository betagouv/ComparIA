"""Column types that keep a secret encrypted in the database.

The Python side sees the plain value; the row holds a Fernet token made with
`COMPARIA_ENCRYPTION_KEY` (see `utils.secrets`). Rotating the key means
adding the new one in front and running `comparia-cli db reencrypt-secrets`.

A token no configured key opens reads as an `UnreadableSecret`, not as None:
the secret is there, the operator dropped its key too early. SQLAlchemy
decodes a whole result set at once, so raising here would fail every row of
the query for one bad one; the marker lets each reader deal with its own row.
"""

from dataclasses import dataclass
from typing import Any

from sqlalchemy import String, TypeDecorator
from sqlalchemy.dialects.postgresql import JSONB

from utils.secrets import SecretUnreadableError, decrypt_secret, encrypt_secret


class UnreadableSecret:
    """A stored secret that no configured key opens.

    Truthy, so "is a secret set" stays true. Not a str, so it cannot be sent
    to a provider by mistake: turning it into text raises
    SecretUnreadableError. Written back, it puts the token it came from into
    the row unchanged, so a save cannot destroy what a key rotation could
    still recover.
    """

    __slots__ = ("token",)

    def __init__(self, token: str) -> None:
        self.token = token

    def __repr__(self) -> str:
        return "UnreadableSecret()"

    def __str__(self) -> str:
        raise SecretUnreadableError()


@dataclass(frozen=True)
class UnreadableRow:
    """Where a secret no configured key opens is stored: what an error names
    instead of the value."""

    table: str
    row_id: Any
    column: str

    def __str__(self) -> str:
        return f"{self.table} {self.row_id}.{self.column}"

    def message(self) -> str:
        return f"{self} cannot be decrypted with COMPARIA_ENCRYPTION_KEY"


def _read(token: str) -> str | UnreadableSecret:
    try:
        return decrypt_secret(token)
    except SecretUnreadableError:
        return UnreadableSecret(token)


def _write(value: str | UnreadableSecret) -> str:
    if isinstance(value, UnreadableSecret):
        return value.token
    return encrypt_secret(value)


class EncryptedStr(TypeDecorator):
    """A string column stored encrypted. An empty string is kept as is."""

    impl = String
    cache_ok = True

    def process_bind_param(self, value: Any, dialect: Any) -> str | None:
        if not value:
            return value
        return _write(value)

    def process_result_value(self, value: str | None, dialect: Any) -> Any:
        if not value:
            return value
        return _read(value)


class EncryptedJSONFields(TypeDecorator):
    """A JSONB column whose named fields are stored encrypted.

    `secret_fields` maps the value of the `kind` key to the fields to protect,
    so one column can hold several shapes.
    """

    impl = JSONB
    cache_ok = True

    def __init__(self, secret_fields: dict[str, tuple[str, ...]]) -> None:
        super().__init__()
        self._secret_fields = dict(secret_fields)
        # Constructor arguments make the statement cache key, which has to be
        # hashable: a dict is not, a sorted tuple of tuples is.
        self.secret_fields = tuple(
            sorted((kind, tuple(fields)) for kind, fields in secret_fields.items())
        )

    def _fields(self, value: dict) -> tuple[str, ...]:
        return self._secret_fields.get(value.get("kind"), ())

    def _map(self, value: Any, transform: Any) -> Any:
        if not isinstance(value, dict):
            return value
        out = dict(value)
        for field in self._fields(out):
            if out.get(field):
                out[field] = transform(out[field])
        return out

    def process_bind_param(self, value: Any, dialect: Any) -> Any:
        return self._map(value, _write)

    def process_result_value(self, value: Any, dialect: Any) -> Any:
        return self._map(value, _read)

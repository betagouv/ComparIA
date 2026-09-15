import uuid
import zlib
from datetime import datetime, timezone
from typing import Annotated, Literal, get_args

from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlmodel import Field, SQLModel

BotPos = Literal["a", "b"]
BOT_POS: tuple[BotPos, ...] = get_args(BotPos)


def utc_now() -> datetime:
    """Naive UTC, unlike AutoDatetime which stores the host's local time."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def as_naive_utc(value: datetime) -> datetime:
    """Bring a caller-supplied timestamp onto the same scale as utc_now().

    An aware value handed to the driver is silently converted to the database
    session's zone and loses its offset, so columns that should agree end up
    hours apart. Naive values are assumed to be UTC already.
    """
    if value.tzinfo is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def escape_like(value: str) -> str:
    """Neutralise the LIKE wildcards in a user-supplied search term.

    Binding the term stops SQL injection but not `%` and `_`, which still mean
    "anything" to LIKE: a search for `_` matches every row. Pass `escape="\\"`
    to `ilike()` alongside this. Lives here because the admin and suggestion
    searches both need it and share nothing else.
    """
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def logo_version(data: bytes | None) -> str | None:
    """A short tag that changes whenever the stored logo does.

    It goes in the logo URL so the browser can keep the bytes for a year and
    still fetch a new upload. Derived from the content rather than counted, so
    there is no counter to forget to bump. Not a security hash: crc32 is enough
    to tell two uploads apart.
    """
    if data is None:
        return None
    return f"{zlib.crc32(data):08x}"


ModelId = Annotated[
    uuid.UUID,
    Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        schema_extra={"json_schema_extra": {"hidden": True, "disabled": True}},
    ),
]
AutoDatetime = Annotated[
    datetime, Field(default_factory=datetime.now, sa_type=TIMESTAMP)
]
UtcDatetime = Annotated[datetime, Field(default_factory=utc_now, sa_type=TIMESTAMP)]
OptionalDatetime = Annotated[datetime | None, Field(sa_type=TIMESTAMP)]
Datetime = Annotated[datetime, Field(sa_type=TIMESTAMP)]


class BaseDBModel(SQLModel):
    id: ModelId
    created_at: AutoDatetime
    updated_at: AutoDatetime

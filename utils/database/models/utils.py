import uuid
from datetime import datetime, timezone
from typing import Annotated, Literal, get_args

from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlmodel import Field, SQLModel

BotPos = Literal["a", "b"]
BOT_POS: tuple[BotPos, ...] = get_args(BotPos)


def utc_now() -> datetime:
    """Naive UTC, unlike AutoDatetime which stores the host's local time."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


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

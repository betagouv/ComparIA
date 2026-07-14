import uuid
from datetime import datetime
from typing import Annotated, Literal, get_args

from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlmodel import Field, SQLModel

BotPos = Literal["a", "b"]
BOT_POS: tuple[BotPos, ...] = get_args(BotPos)

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
OptionalDatetime = Annotated[datetime | None, Field(sa_type=TIMESTAMP)]
Datetime = Annotated[datetime, Field(sa_type=TIMESTAMP)]


class BaseDBModel(SQLModel):
    id: ModelId
    created_at: AutoDatetime
    updated_at: AutoDatetime

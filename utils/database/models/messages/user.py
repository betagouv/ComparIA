import uuid
from typing import Annotated, Literal

from sqlmodel import Field, SQLModel, String

from ..utils import AutoDatetime, ModelId


class UserMessageBase(SQLModel):
    id: ModelId
    created_at: AutoDatetime
    role: Annotated[Literal["user"], Field(sa_type=String)] = "user"
    content: str

    turn_id: uuid.UUID | None = Field(default=None, foreign_key="turn.id", unique=True)


class UserMessage(UserMessageBase, table=True):
    __tablename__ = "user_message"


class UserMessageCreate(UserMessageBase):
    pass


class UserMessageRead(UserMessageBase):
    pass

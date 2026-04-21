from typing import Annotated, Literal

from sqlmodel import Field, SQLModel, String


class UserMessageBase(SQLModel):
    role: Annotated[Literal["user"], Field(sa_type=String)] = "user"
    content: str

    turn_id: int | None = Field(default=None, foreign_key="turn.id", unique=True)


class UserMessage(UserMessageBase, table=True):
    __tablename__ = "user_message"

    id: Annotated[int | None, Field(primary_key=True)] = None


class UserMessageCreate(UserMessageBase):
    pass


class UserMessageRead(UserMessageBase):
    id: int

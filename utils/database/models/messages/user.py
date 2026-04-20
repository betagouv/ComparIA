from typing import Annotated, Literal

from sqlmodel import Field, SQLModel, String


class UserMessage(SQLModel, table=True):
    __tablename__ = "user_message"

    id: Annotated[int | None, Field(primary_key=True)] = None
    role: Annotated[Literal["user"], Field(sa_type=String)] = "user"
    content: str

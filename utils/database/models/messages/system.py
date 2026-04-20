from typing import Annotated, Literal

from sqlmodel import Field, SQLModel, String


class SystemMessage(SQLModel, table=True):
    __tablename__ = "system_message"

    id: Annotated[int | None, Field(primary_key=True)] = None
    role: Annotated[Literal["system"], Field(sa_type=String)] = "system"
    content: str

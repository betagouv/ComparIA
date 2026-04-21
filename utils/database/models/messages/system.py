from typing import Annotated, Literal

from sqlmodel import Field, SQLModel, String


class SystemMessageBase(SQLModel):
    role: Annotated[Literal["system"], Field(sa_type=String)] = "system"
    content: str


class SystemMessage(SystemMessageBase, table=True):
    __tablename__ = "system_message"

    id: Annotated[int | None, Field(primary_key=True)] = None


class SystemMessageCreate(SystemMessageBase):
    pass


class SystemMessageRead(SystemMessageBase):
    id: int

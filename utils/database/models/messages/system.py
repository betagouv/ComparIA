from typing import Annotated, Literal

from sqlmodel import Field, SQLModel, String

from ..utils import AutoDatetime, ModelId


class SystemMessageBase(SQLModel):
    id: ModelId
    created_at: AutoDatetime
    role: Annotated[Literal["system"], Field(sa_type=String)] = "system"
    content: str


class SystemMessage(SystemMessageBase, table=True):
    __tablename__ = "system_message"


class SystemMessageCreate(SystemMessageBase):
    pass


class SystemMessageRead(SystemMessageBase):
    pass

import uuid
from typing import Annotated, Literal

from linkup import LinkupSearchTextResult
from pydantic import FieldSerializationInfo, field_serializer
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel, String

from backend.arena.web_search import merge_web_search_with_content

from ..utils import AutoDatetime, ModelId


class UserMessageBase(SQLModel):
    id: ModelId
    created_at: AutoDatetime
    role: Annotated[Literal["user"], Field(sa_type=String)] = "user"
    content: str
    web_search_results: Annotated[
        list[LinkupSearchTextResult] | None, Field(sa_type=JSONB)
    ] = None

    turn_id: uuid.UUID | None = Field(default=None, foreign_key="turn.id", unique=True)


class UserMessage(UserMessageBase, table=True):
    __tablename__ = "user_message"


class UserMessageCreate(UserMessageBase):
    pass


class UserMessageRead(UserMessageBase):

    @field_serializer("content", mode="plain")
    def override_content(self, content: str, info: FieldSerializationInfo) -> str:
        """
        If "merge_web_search" in context, embeds web search results in content for litellm.
        """
        context = info.context if isinstance(info.context, dict) else {}

        if self.web_search_results and context.get("merge_web_search"):
            return merge_web_search_with_content(content, self.web_search_results)

        return content

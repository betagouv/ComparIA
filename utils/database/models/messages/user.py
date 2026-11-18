import uuid
from typing import Annotated, Literal

from linkup import LinkupSearchTextResult
from pydantic import FieldSerializationInfo, computed_field, field_serializer
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel, String

from backend.config import WEB_SEARCH_INTRO

from ..utils import AutoDatetime, ModelId


def merge_web_search_with_content(
    content: str, web_search_results: list[LinkupSearchTextResult] | list[dict]
) -> str:
    # A message read from the database holds the results as the dicts the
    # JSONB column returns, not as results.
    results = [LinkupSearchTextResult.model_validate(r) for r in web_search_results]
    return "\n\n".join(
        [
            content,
            WEB_SEARCH_INTRO,
            "\n\n---\n\n".join(
                [
                    f"Source: {result.name} ({result.url})\n{result.content}".strip()
                    for result in results
                ]
            ),
        ]
    )


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

    @computed_field  # type: ignore[prop-decorator]
    @property
    def user_content(self) -> str:
        return self.content

    @field_serializer("content", mode="plain")
    def override_content(self, content: str, info: FieldSerializationInfo) -> str:
        """
        If "merge_sources" in context, embeds the sources this message carries in its content.
        """
        context = info.context if isinstance(info.context, dict) else {}

        if self.web_search_results and context.get("merge_sources"):
            return merge_web_search_with_content(content, self.web_search_results)

        return content

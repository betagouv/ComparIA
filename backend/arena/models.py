"""
Data validation models using Pydantic.

Defines all data structures for:
- Conversation data (messages, participant info, metadata)
"""

import datetime
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field

from backend.language_models.models import Endpoint, LanguageModel


class BaseMessage(BaseModel):
    """
    Single message in a conversation.

    Represents one user or assistant message with content and metadata.
    Assistant messages MUST include output_tokens for tracking.

    Attributes:
        role: "user", "assistant", or "system"
        content: Message text content
        metadata: Additional data (output_tokens for assistant messages, etc.)
    """

    role: Literal["user", "assistant", "system"]
    content: str


class SystemMessage(BaseMessage):
    role: Literal["system"] = "system"


class UserMessage(BaseMessage):
    role: Literal["user"] = "user"


class AssistantMessage(BaseMessage):
    class AssistantMessageMetadata(BaseModel):
        generation_id: str
        bot: Literal["a", "b"]
        output_tokens: int
        duration: int | None

    role: Literal["assistant"] = "assistant"
    error: str | None = None
    reasoning: str | None = None
    metadata: AssistantMessageMetadata


AnyMessage = SystemMessage | UserMessage | AssistantMessage


class Conversation(BaseModel):
    """
    Represents a conversation with a single AI model.

    Stores messages, model information, and metadata about the conversation.
    Each conversation has a unique ID and tracks the model's endpoint for API calls.
    """

    conv_id: str = Field(default_factory=lambda: str(uuid4()).replace("-", ""))
    model_name: str
    endpoint: Endpoint
    messages: list[AnyMessage]

    @property
    def has_system_msg(self) -> bool:
        return isinstance(self.messages[0], SystemMessage)

    @property
    def opening_msg(self) -> str:
        return self.messages[1 if self.has_system_msg else 0].content

    @property
    def conv_turns(self) -> int:
        """
        Count the number of conversation turns (user messages or exchanges).

        A turn is one user message and one llm response pair.

        Args:
            messages: List of ChatMessage objects

        Returns:
            int: Number of turns (exchanges between user and llm)
        """
        # If first message is system prompt, skip it in count
        return (len(self.messages) - (1 if self.has_system_msg else 0)) // 2


def create_conversation(llm: LanguageModel, user_msg: UserMessage) -> Conversation:
    messages: list[AnyMessage] = (
        [SystemMessage(content=llm.system_prompt), user_msg]
        if llm.system_prompt
        else [user_msg]
    )

    return Conversation(model_name=llm.id, endpoint=llm.endpoint, messages=messages)


class Conversations(BaseModel):
    """
    Complete conversation record with both models' responses and metadata.

    Stores a paired comparison between two models on the same prompts.
    Used to persist conversation data to database and JSON logs.
    """

    conversation_a: Conversation
    conversation_b: Conversation

    def record(self) -> None:
        # FIXME use custom serializer?
        data = self.model_dump()
        conv = self.conversation_a
        data["conversation_pair_id"] = (
            f"{self.conversation_a.conv_id}-{self.conversation_b.conv_id}"
        )
        data["opening_msg"] = conv.opening_msg
        data["conv_turns"] = conv.conv_turns


def create_conversations(
    llm_a: LanguageModel, llm_b: LanguageModel, user_prompt: str
) -> Conversations:
    user_msg = UserMessage(role="user", content=user_prompt)
    conv_a = create_conversation(llm_a, user_msg)
    conv_b = create_conversation(llm_b, user_msg)

    return Conversations(conversation_a=conv_a, conversation_b=conv_b)


# class Conversation(BaseModel):
#     """
#     Complete conversation record with both models' responses and metadata.

#     Stores a paired comparison between two models on the same prompts.
#     Used to persist conversation data to database and JSON logs.

#     Attributes:
#         id: Internal database ID
#         timestamp: When conversation was created
#         model_a_name/model_b_name: Model identifiers
#         conversation_a/conversation_b: Message histories for each model
#         conv_turns: Number of user-model exchange rounds
#         system_prompt_a/b: System prompts used (if any)
#         conversation_pair_id: Unique ID combining both conv IDs
#         conv_a_id/conv_b_id: Individual conversation IDs
#         session_hash: User session identifier
#         visitor_id: Matomo visitor tracking ID (if enabled)
#         ip: User's IP address (PII)
#         model_pair_name: Sorted model pair for analysis
#         opening_msg: Initial user prompt
#         archived: Whether conversation is archived
#         mode: Model selection mode (random, big-vs-small, etc.)
#         custom_models_selection: Custom model selection if mode=custom
#         short_summary: Auto-generated summary (added during post-processing)
#         keywords/categories/languages: Extracted metadata (post-processing)
#         pii_analyzed/contains_pii: PII detection results
#         total_conv_a_output_tokens/total_conv_b_output_tokens: Token usage
#         ip_map: Geographic region derived from IP
#         postprocess_failed: Whether post-processing failed
#     """

#     id: int
#     timestamp: datetime.datetime = Field(default_factory=datetime.datetime.now)
#     model_a_name: str
#     model_b_name: str
#     conversation_a: ConversationMessages
#     conversation_b: ConversationMessages
#     conv_turns: int = 0
#     system_prompt_a: str | None = None
#     system_prompt_b: str | None = None
#     conversation_pair_id: str
#     conv_a_id: str
#     conv_b_id: str
#     session_hash: str
#     visitor_id: str | None = None
#     ip: str | None = None  # Warning: PII
#     model_pair_name: str
#     opening_msg: str
#     archived: bool = False
#     mode: str | None = None
#     custom_models_selection: dict[str, Any] | None = None
#     short_summary: str | None = None
#     keywords: dict[str, Any] | None = None
#     categories: dict[str, Any] | None = None
#     languages: dict[str, Any] | None = None
#     pii_analyzed: bool = False
#     contains_pii: bool | None = None
#     total_conv_a_output_tokens: int | None = None
#     total_conv_b_output_tokens: int | None = None
#     ip_map: str | None = None
#     postprocess_failed: bool = False

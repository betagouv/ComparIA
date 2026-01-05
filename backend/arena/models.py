"""
Data validation models using Pydantic.

Defines all data structures for:
- Conversation data (messages, participant info, metadata)
"""

import datetime
from dataclasses import dataclass, field
from typing import Any, Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, Field, RootModel, model_validator

from backend.language_models.models import Endpoint, LanguageModel


# Legacy metadata model (kept for compatibility)
class Metadata(BaseModel):
    """Metadata for chat messages."""

    bot: Optional[Literal["a", "b"]] = None
    duration: Optional[float] = None
    generation_id: Optional[str] = None
    output_tokens: Optional[int] = None


@dataclass
class ChatMessage:
    """
    Chat message dataclass for Gradio compatibility.

    Used for frontend communication and during streaming (flexible metadata).
    Will be converted to AnyMessage types for persistence.
    """

    role: Literal["user", "assistant", "system"]
    content: str
    error: Optional[str] = None
    reasoning: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)


# New message hierarchy from commit 6b42a0964b34
class BaseMessage(BaseModel):
    """
    Base message class with strict typing.

    All messages have a role and content.
    """

    role: Literal["user", "assistant", "system"]
    content: str


class SystemMessage(BaseMessage):
    """System prompt message."""

    role: Literal["system"] = "system"


class UserMessage(BaseMessage):
    """User input message."""

    role: Literal["user"] = "user"


class AssistantMessage(BaseMessage):
    """
    Assistant response message with required metadata.

    Metadata must include generation_id, bot, and output_tokens.
    """

    class AssistantMessageMetadata(BaseModel):
        generation_id: str
        bot: Literal["a", "b"]
        output_tokens: int
        duration: float | None = None

    role: Literal["assistant"] = "assistant"
    error: str | None = None
    reasoning: str | None = None
    metadata: AssistantMessageMetadata


# Union type for any message
AnyMessage = SystemMessage | UserMessage | AssistantMessage


# Legacy ConversationMessage (kept for backward compatibility)
class ConversationMessage(BaseModel):
    """
    Single message in a conversation (legacy).

    DEPRECATED: Use AnyMessage types instead.
    """

    role: str
    content: str
    metadata: dict[str, Any] | None = None

    @model_validator(mode="after")
    def check_assistant_metadata(self) -> "ConversationMessage":
        if self.role == "assistant":
            if not self.metadata or "output_tokens" not in self.metadata:
                raise ValueError(
                    "Assistant messages must have 'output_tokens' in metadata"
                )
        return self


# Type alias for list of messages
ConversationMessages = RootModel[list[ConversationMessage]]


# New Conversation model (runtime, single model)
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
        return len(self.messages) > 0 and isinstance(self.messages[0], SystemMessage)

    @property
    def opening_msg(self) -> str:
        return self.messages[1 if self.has_system_msg else 0].content

    @property
    def conv_turns(self) -> int:
        """
        Count the number of conversation turns (user messages or exchanges).

        A turn is one user message and one llm response pair.
        """
        return (len(self.messages) - (1 if self.has_system_msg else 0)) // 2


def create_conversation(llm: LanguageModel, user_msg: UserMessage) -> Conversation:
    """Create a single conversation with system prompt if configured."""
    messages: list[AnyMessage] = (
        [SystemMessage(content=llm.system_prompt), user_msg]
        if llm.system_prompt
        else [user_msg]
    )

    return Conversation(model_name=llm.id, endpoint=llm.endpoint, messages=messages)


# New Conversations model (paired conversations for arena)
class Conversations(BaseModel):
    """
    Paired conversations for arena comparison.

    Wraps two Conversation objects for type-safe handling.
    """

    conversation_a: Conversation
    conversation_b: Conversation

    @property
    def session_id(self) -> str:
        """Generate session identifier from both conv IDs."""
        return f"{self.conversation_a.conv_id}-{self.conversation_b.conv_id}"

    def record(self) -> None:
        """
        Record conversation data (placeholder).

        TODO: Implement database persistence.
        """
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
    """Create paired conversations for arena comparison."""
    user_msg = UserMessage(content=user_prompt)
    conv_a = create_conversation(llm_a, user_msg)
    conv_b = create_conversation(llm_b, user_msg)

    return Conversations(conversation_a=conv_a, conversation_b=conv_b)


# Database model (renamed from Conversation to avoid collision)
class ConversationRecord(BaseModel):
    """
    Database record for a paired conversation comparison.

    Stores complete conversation data from both models for PostgreSQL persistence.
    This is the model used for database operations and post-processing.
    """

    id: int
    timestamp: datetime.datetime = Field(default_factory=datetime.datetime.now)
    model_a_name: str
    model_b_name: str
    conversation_a: ConversationMessages
    conversation_b: ConversationMessages
    conv_turns: int = 0
    system_prompt_a: str | None = None
    system_prompt_b: str | None = None
    conversation_pair_id: str
    conv_a_id: str
    conv_b_id: str
    session_hash: str
    visitor_id: str | None = None
    ip: str | None = None  # Warning: PII
    model_pair_name: str
    opening_msg: str
    archived: bool = False
    mode: str | None = None
    custom_models_selection: dict[str, Any] | None = None
    short_summary: str | None = None
    keywords: dict[str, Any] | None = None
    categories: dict[str, Any] | None = None
    languages: dict[str, Any] | None = None
    pii_analyzed: bool = False
    contains_pii: bool | None = None
    total_conv_a_output_tokens: int | None = None
    total_conv_b_output_tokens: int | None = None
    ip_map: str | None = None
    postprocess_failed: bool = False


# Request/Response models for FastAPI endpoints


class AddTextRequest(BaseModel):
    """Request body for adding a message to an existing conversation."""

    session_hash: str
    message: str = Field(min_length=1)


class RetryRequest(BaseModel):
    """Request body for retrying the last bot response."""

    session_hash: str


class ReactRequest(BaseModel):
    """Request body for updating message reactions."""

    reaction_json: dict[str, Any]  # Reaction data with index, liked, prefs, comment


class VoteRequest(BaseModel):
    """Request body for submitting a vote after conversation."""

    which_model_radio_output: str  # "model-a", "model-b", or "both-equal"
    positive_a_output: list[str] = Field(default_factory=list)
    positive_b_output: list[str] = Field(default_factory=list)
    negative_a_output: list[str] = Field(default_factory=list)
    negative_b_output: list[str] = Field(default_factory=list)
    comments_a_output: str = ""
    comments_b_output: str = ""


class RevealData(BaseModel):
    """Response data revealing model identities after vote."""

    model_a: str
    model_b: str
    model_a_metadata: dict[str, Any]
    model_b_metadata: dict[str, Any]

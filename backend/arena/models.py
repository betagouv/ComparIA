"""
Data validation models using Pydantic.

Defines all data structures for:
- Conversation data (messages, participant info, metadata)
"""

import datetime
from dataclasses import dataclass, field
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, RootModel, model_validator


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

    Used for frontend communication with similar structure to Gradio's ChatMessage.
    """

    role: Literal["user", "assistant", "system"]
    content: str
    error: Optional[str] = None
    reasoning: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)


class ConversationMessage(BaseModel):
    """
    Single message in a conversation.

    Represents one user or assistant message with content and metadata.
    Assistant messages MUST include output_tokens for tracking.

    Attributes:
        role: "user", "assistant", or "system"
        content: Message text content
        metadata: Additional data (output_tokens for assistant messages, etc.)
    """

    role: str
    content: str
    metadata: dict[str, Any] | None = None

    # Validate that assistant messages include token counts
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


class Conversation(BaseModel):
    """
    Complete conversation record with both models' responses and metadata.

    Stores a paired comparison between two models on the same prompts.
    Used to persist conversation data to database and JSON logs.

    Attributes:
        id: Internal database ID
        timestamp: When conversation was created
        model_a_name/model_b_name: Model identifiers
        conversation_a/conversation_b: Message histories for each model
        conv_turns: Number of user-model exchange rounds
        system_prompt_a/b: System prompts used (if any)
        conversation_pair_id: Unique ID combining both conv IDs
        conv_a_id/conv_b_id: Individual conversation IDs
        session_hash: User session identifier
        visitor_id: Matomo visitor tracking ID (if enabled)
        ip: User's IP address (PII)
        model_pair_name: Sorted model pair for analysis
        opening_msg: Initial user prompt
        archived: Whether conversation is archived
        mode: Model selection mode (random, big-vs-small, etc.)
        custom_models_selection: Custom model selection if mode=custom
        short_summary: Auto-generated summary (added during post-processing)
        keywords/categories/languages: Extracted metadata (post-processing)
        pii_analyzed/contains_pii: PII detection results
        total_conv_a_output_tokens/total_conv_b_output_tokens: Token usage
        ip_map: Geographic region derived from IP
        postprocess_failed: Whether post-processing failed
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
    """Request body for updating message reactions (like/dislike)."""

    session_hash: str
    message_id: str
    reaction: str | None  # "like", "dislike", or None to remove


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

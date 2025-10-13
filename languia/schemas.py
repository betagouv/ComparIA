from pydantic import BaseModel, Field, model_validator, ValidationError
from typing import List, Optional, Dict, Any
import datetime


class ConversationMessage(BaseModel):
    role: str
    content: str
    metadata: Optional[Dict[str, Any]] = None

    # Custom validation to ensure 'output_tokens' is present for 'assistant' roles
    @model_validator(mode="after")
    def check_assistant_metadata(self) -> "ConversationMessage":
        if self.role == "assistant":
            if not self.metadata or "output_tokens" not in self.metadata:
                raise ValueError("Assistant messages must have 'output_tokens' in metadata")
        return self


class Conversation(BaseModel):
    id: int
    # TODO: fuseau horaire
    timestamp: datetime.datetime = Field(default_factory=datetime.datetime.now)
    model_a_name: str
    model_b_name: str
    conversation_a: List[ConversationMessage]
    conversation_b: List[ConversationMessage]
    conv_turns: int = 0
    system_prompt_a: Optional[str] = None
    system_prompt_b: Optional[str] = None
    conversation_pair_id: str
    conv_a_id: str
    conv_b_id: str
    session_hash: str
    visitor_id: Optional[str] = None
    ip: Optional[str] = None
    model_pair_name: str
    opening_msg: str
    selected_category: Optional[str] = None
    # TODO: from database to dataset (computed)
    is_unedited_prompt: Optional[bool] = None
    archived: bool = False
    mode: Optional[str] = None
    custom_models_selection: Optional[Dict[str, Any]] = None
    short_summary: Optional[str] = None
    keywords: Optional[Dict[str, Any]] = None
    categories: Optional[Dict[str, Any]] = None
    languages: Optional[Dict[str, Any]] = None
    pii_analyzed: bool = False
    contains_pii: Optional[bool] = None
    conversation_a_pii_removed: Optional[List[ConversationMessage]] = None
    conversation_b_pii_removed: Optional[List[ConversationMessage]] = None
    opening_msg_pii_removed: Optional[str] = None
    total_conv_a_output_tokens: Optional[int] = None
    total_conv_b_output_tokens: Optional[int] = None
    ip_map: Optional[str] = None
    postprocess_failed: bool = False

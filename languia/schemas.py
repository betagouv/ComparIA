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
    # TODO: from db to dataset only (computed)
    # model_a_total_params: Optional[float] = None
    # model_a_active_params: Optional[float] = None
    # model_b_active_params: Optional[float] = None
    # model_b_total_params: Optional[float] = None
    # total_conv_a_kwh: Optional[float] = None
    # total_conv_b_kwh: Optional[float] = None
    ip_map: Optional[str] = None
    postprocess_failed: bool = False


# class Vote(BaseModel):
#     id: Optional[int] = None
#     timestamp: datetime.datetime = Field(default_factory=datetime.datetime.now)
#     model_a_name: str
#     model_b_name: str
#     model_pair_name: Optional[List[str]] = None
#     chosen_model_name: Optional[str] = None
#     opening_msg: str
#     both_equal: Optional[bool] = None
#     conversation_a: List[ConversationMessage]
#     conversation_b: List[ConversationMessage]
#     conv_turns: Optional[int] = None
#     system_prompt_a: Optional[str] = None
#     system_prompt_b: Optional[str] = None
#     selected_category: Optional[str] = None
#     is_unedited_prompt: Optional[bool] = None
#     conversation_pair_id: str
#     session_hash: Optional[str] = None
#     visitor_id: Optional[str] = None
#     ip: Optional[str] = None
#     conv_comments_a: Optional[str] = None
#     conv_comments_b: Optional[str] = None
#     conv_useful_a: Optional[bool] = None
#     conv_useful_b: Optional[bool] = None
#     conv_complete_a: Optional[bool] = None
#     conv_complete_b: Optional[bool] = None
#     conv_creative_a: Optional[bool] = None
#     conv_creative_b: Optional[bool] = None
#     conv_clear_formatting_a: Optional[bool] = None
#     conv_clear_formatting_b: Optional[bool] = None
#     conv_incorrect_a: Optional[bool] = None
#     conv_incorrect_b: Optional[bool] = None
#     conv_superficial_a: Optional[bool] = None
#     conv_superficial_b: Optional[bool] = None
#     conv_instructions_not_followed_a: Optional[bool] = None
#     conv_instructions_not_followed_b: Optional[bool] = None
#     archived: bool = False


# class Reaction(BaseModel):
#     id: Optional[int] = None
#     timestamp: datetime.datetime = Field(default_factory=datetime.datetime.now)
#     model_a_name: str
#     model_b_name: str
#     refers_to_model: Optional[str] = None
#     msg_index: int
#     opening_msg: str
#     conversation_a: List[ConversationMessage]
#     conversation_b: List[ConversationMessage]
#     model_pos: Optional[str] = None
#     conv_turns: int
#     system_prompt: Optional[str] = None
#     conversation_pair_id: str
#     conv_a_id: str
#     conv_b_id: str
#     refers_to_conv_id: str
#     session_hash: Optional[str] = None
#     visitor_id: Optional[str] = None
#     ip: Optional[str] = None
#     country: Optional[str] = None
#     city: Optional[str] = None
#     response_content: Optional[str] = None
#     question_content: Optional[str] = None
#     liked: Optional[bool] = None
#     disliked: Optional[bool] = None
#     comment: Optional[str] = None
#     useful: Optional[bool] = None
#     complete: Optional[bool] = None
#     creative: Optional[bool] = None
#     clear_formatting: Optional[bool] = None
#     incorrect: Optional[bool] = None
#     superficial: Optional[bool] = None
#     instructions_not_followed: Optional[bool] = None
#     model_pair_name: Optional[List[str]] = None
#     msg_rank: int
#     chatbot_index: int
#     question_id: Optional[str] = None
#     archived: bool = False
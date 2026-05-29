from .llm import LLMMessage, LLMMessageCreate, LLMMessageFinal, LLMMessageRead
from .system import SystemMessage, SystemMessageCreate, SystemMessageRead
from .user import UserMessage, UserMessageCreate, UserMessageRead

AnyMessageRead = LLMMessageRead | SystemMessageRead | UserMessageRead

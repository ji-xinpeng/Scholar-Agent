from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, AsyncGenerator
from dataclasses import dataclass, field
from enum import Enum


class MessageRole(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass
class ChatMessage:
    role: MessageRole
    content: str
    name: Optional[str] = None
    tool_call_id: Optional[str] = None


@dataclass
class ChatResponse:
    content: str
    model: str
    usage: Dict[str, int] = field(default_factory=dict)
    finish_reason: Optional[str] = None
    raw_response: Optional[Any] = None


class BaseLLM(ABC):
    """LLM 基类，定义所有大模型必须实现的接口"""

    name: str = ""
    default_model: str = ""
    supported_models: List[str] = []

    def __init__(self, api_key: str, base_url: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model or self.default_model
        self._validate_model()

    def _validate_model(self):
        if self.supported_models and self.model not in self.supported_models:
            raise ValueError(f"Model {self.model} not supported. Available: {self.supported_models}")

    @abstractmethod
    async def chat(
        self,
        messages: List[ChatMessage],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        top_p: float = 1.0,
        stream: bool = False,
        **kwargs
    ) -> ChatResponse:
        """非流式对话"""
        pass

    @abstractmethod
    async def chat_stream(
        self,
        messages: List[ChatMessage],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        top_p: float = 1.0,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """流式对话"""
        pass

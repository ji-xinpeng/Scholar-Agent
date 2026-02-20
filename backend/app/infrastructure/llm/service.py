from typing import List, Optional, AsyncGenerator
from functools import lru_cache
from openai import AsyncOpenAI
from dataclasses import dataclass, field
from enum import Enum

from app.core.config import settings
from app.infrastructure.logging.config import logger


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
    usage: dict = field(default_factory=dict)
    finish_reason: Optional[str] = None
    raw_response: Optional[any] = None


class DoubaoLLM:
    """豆包大模型"""

    name = "doubao"
    default_model = "doubao-seed-2-0-mini-260215"
    supported_models = [
        "doubao-seedream-4-5-251128",
        "doubao-seed-2-0-mini-260215",
        "doubao-seed-2-0-lite-260215",
        "doubao-seed-2-0-pro-260215",
        "doubao-seed-2-0-code-preview-260215",
        "doubao-embedding-large-text-250515",
        "doubao-embedding-vision-251215"
    ]

    def __init__(self, api_key: str, base_url: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key
        self.base_url = base_url or "https://ark.cn-beijing.volces.com/api/v3"
        self.model = model or self.default_model
        
        if not api_key:
            raise ValueError("API key is required for DoubaoLLM")
        
        if self.model not in self.supported_models:
            logger.warning(f"Model '{self.model}' not in supported models list. Using default model '{self.default_model}'.")
            self.model = self.default_model
        
        self.client = AsyncOpenAI(
            base_url=self.base_url,
            api_key=self.api_key
        )

    def _convert_messages(self, messages: List[ChatMessage]) -> List[dict]:
        converted = []
        for msg in messages:
            converted_msg = {"role": msg.role.value, "content": msg.content}
            if msg.name:
                converted_msg["name"] = msg.name
            converted.append(converted_msg)
        return converted

    async def chat(
        self,
        messages: List[ChatMessage],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        top_p: float = 1.0,
        stream: bool = False,
        **kwargs
    ) -> ChatResponse:
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=self._convert_messages(messages),
                temperature=temperature,
                top_p=top_p,
                max_tokens=max_tokens,
                stream=stream
            )

            choice = response.choices[0]
            return ChatResponse(
                content=choice.message.content,
                model=self.model,
                usage=response.usage.model_dump() if response.usage else {},
                finish_reason=choice.finish_reason,
                raw_response=response.model_dump()
            )
        except Exception as e:
            logger.error(f"DoubaoLLM chat 调用失败: {e}", exc_info=True)
            raise

    async def chat_stream(
        self,
        messages: List[ChatMessage],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        top_p: float = 1.0,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        try:
            stream = await self.client.chat.completions.create(
                model=self.model,
                messages=self._convert_messages(messages),
                temperature=temperature,
                top_p=top_p,
                max_tokens=max_tokens,
                stream=True
            )

            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            logger.error(f"DoubaoLLM chat_stream 调用失败: {e}", exc_info=True)
            raise


class LLMService:
    """LLM 服务层"""

    def __init__(self):
        self._llm = None
        self._initialize_llm()

    def _initialize_llm(self):
        """初始化豆包 LLM 实例"""
        if not settings.DOUBAO_API_KEY:
            error_msg = "豆包(Doubao) API Key 未配置，请在 config.py 中设置 DOUBAO_API_KEY"
            logger.error(error_msg)
            raise ValueError(error_msg)

        logger.info(f"初始化豆包(Doubao) LLM - 模型: {settings.DOUBAO_MODEL}")
        self._llm = DoubaoLLM(
            api_key=settings.DOUBAO_API_KEY,
            base_url=settings.DOUBAO_BASE_URL,
            model=settings.DOUBAO_MODEL
        )

    def get_llm(self, model: Optional[str] = None) -> DoubaoLLM:
        """获取 LLM 实例"""
        if model and model != self._llm.model:
            logger.info(f"切换模型: {self._llm.model} -> {model}")
            return DoubaoLLM(
                api_key=settings.DOUBAO_API_KEY,
                base_url=settings.DOUBAO_BASE_URL,
                model=model
            )
        return self._llm

    async def chat(
        self,
        messages: List[ChatMessage],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        top_p: float = 1.0,
        stream: bool = False,
        **kwargs
    ) -> ChatResponse:
        """非流式对话"""
        logger.debug(f"调用豆包聊天 - 模型: {model or settings.DOUBAO_MODEL}, 消息数: {len(messages)}, 温度: {temperature}")
        llm = self.get_llm(model)
        response = await llm.chat(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            stream=stream,
            **kwargs
        )
        logger.debug(f"豆包聊天响应接收 - 模型: {response.model}, 内容长度: {len(response.content)}")
        return response

    async def chat_stream(
        self,
        messages: List[ChatMessage],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        top_p: float = 1.0,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """流式对话"""
        logger.debug(f"开始豆包流式聊天 - 模型: {model or settings.DOUBAO_MODEL}, 消息数: {len(messages)}, 温度: {temperature}")
        llm = self.get_llm(model)
        chunk_count = 0
        async for chunk in llm.chat_stream(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            **kwargs
        ):
            chunk_count += 1
            yield chunk
        logger.debug(f"豆包流式聊天完成 - 总块数: {chunk_count}")

    def list_available_models(self) -> List[str]:
        """列出所有可用的模型"""
        return DoubaoLLM.supported_models


@lru_cache()
def get_llm_service() -> LLMService:
    """获取 LLMService 单例"""
    return LLMService()


llm_service = get_llm_service()

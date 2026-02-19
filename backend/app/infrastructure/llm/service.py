from typing import List, Optional, AsyncGenerator
from functools import lru_cache

from app.core.config import settings
from app.infrastructure.logging.config import logger
from app.infrastructure.llm.base import BaseLLM, ChatMessage, ChatResponse
from app.infrastructure.llm.factory import llm_factory, LLMConfig


class LLMService:
    """LLM 服务层，提供统一的模型调用接口"""

    def __init__(self):
        self._initialize_configs()

    def _initialize_configs(self):
        """从配置文件初始化所有提供商的配置"""
        if settings.QWEN_API_KEY:
            logger.info(f"注册Qwen提供商 - 模型: {settings.QWEN_MODEL}")
            llm_factory.register_config(LLMConfig(
                provider="qwen",
                api_key=settings.QWEN_API_KEY,
                base_url=settings.QWEN_BASE_URL or None,
                model=settings.QWEN_MODEL
            ))

        if settings.DEEPSEEK_API_KEY:
            logger.info(f"注册DeepSeek提供商 - 模型: {settings.DEEPSEEK_MODEL}")
            llm_factory.register_config(LLMConfig(
                provider="deepseek",
                api_key=settings.DEEPSEEK_API_KEY,
                base_url=settings.DEEPSEEK_BASE_URL or None,
                model=settings.DEEPSEEK_MODEL
            ))

    def get_llm(self, provider: Optional[str] = None, model: Optional[str] = None) -> BaseLLM:
        """
        获取 LLM 实例

        Args:
            provider: 提供商名称，不提供则使用默认
            model: 模型名称，不提供则使用默认模型

        Returns:
            BaseLLM 实例
        """
        provider = provider or settings.DEFAULT_LLM_PROVIDER
        return llm_factory.create(provider, model=model)

    async def chat(
        self,
        messages: List[ChatMessage],
        provider: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        top_p: float = 1.0,
        stream: bool = False,
        **kwargs
    ) -> ChatResponse:
        """
        非流式对话

        Args:
            messages: 消息列表
            provider: 提供商名称
            model: 模型名称
            temperature: 温度参数
            max_tokens: 最大 token 数
            top_p: top_p 参数
            stream: 是否流式
            **kwargs: 其他参数

        Returns:
            ChatResponse
        """
        provider = provider or settings.DEFAULT_LLM_PROVIDER
        logger.debug(f"调用大模型聊天 - 提供商: {provider}, 模型: {model or '默认'}, 消息数: {len(messages)}, 温度: {temperature}")
        llm = self.get_llm(provider, model=model)
        response = await llm.chat(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            stream=stream,
            **kwargs
        )
        logger.debug(f"大模型聊天响应接收 - 模型: {response.model}, 内容长度: {len(response.content)}")
        return response

    async def chat_stream(
        self,
        messages: List[ChatMessage],
        provider: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        top_p: float = 1.0,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """
        流式对话

        Args:
            messages: 消息列表
            provider: 提供商名称
            model: 模型名称
            temperature: 温度参数
            max_tokens: 最大 token 数
            top_p: top_p 参数
            **kwargs: 其他参数

        Yields:
            文本片段
        """
        provider = provider or settings.DEFAULT_LLM_PROVIDER
        logger.debug(f"开始大模型流式聊天 - 提供商: {provider}, 模型: {model or '默认'}, 消息数: {len(messages)}, 温度: {temperature}")
        llm = self.get_llm(provider, model=model)
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
        logger.debug(f"大模型流式聊天完成 - 总块数: {chunk_count}")

    def list_available_providers(self) -> List[dict]:
        """
        列出所有可用的提供商

        Returns:
            提供商信息列表
        """
        return llm_factory.list_providers()


@lru_cache()
def get_llm_service() -> LLMService:
    """获取 LLMService 单例"""
    return LLMService()


llm_service = get_llm_service()

from typing import Dict, Type, Optional, List
from dataclasses import dataclass

from app.infrastructure.llm.base import BaseLLM
from app.infrastructure.llm.providers.deepseek import DeepSeekLLM
from app.infrastructure.llm.providers.qwen import QwenLLM


@dataclass
class LLMConfig:
    provider: str
    api_key: str
    base_url: Optional[str] = None
    model: Optional[str] = None


class LLMFactory:
    """LLM 工厂类，负责创建和管理各种大模型实例"""

    def __init__(self):
        self._providers: Dict[str, Type[BaseLLM]] = {}
        self._configs: Dict[str, LLMConfig] = {}
        self._register_default_providers()

    def _register_default_providers(self):
        """注册默认的模型提供商"""
        self.register_provider(QwenLLM)
        self.register_provider(DeepSeekLLM)

    def register_provider(self, provider_cls: Type[BaseLLM]):
        """
        注册新的模型提供商

        Args:
            provider_cls: 继承自 BaseLLM 的提供商类
        """
        if not hasattr(provider_cls, "name") or not provider_cls.name:
            raise ValueError("Provider class must have a 'name' attribute")
        self._providers[provider_cls.name] = provider_cls

    def register_config(self, config: LLMConfig):
        """
        注册模型配置

        Args:
            config: LLMConfig 配置对象
        """
        self._configs[config.provider] = config

    def get_provider(self, provider_name: str) -> Type[BaseLLM]:
        """
        获取指定名称的提供商类

        Args:
            provider_name: 提供商名称

        Returns:
            提供商类

        Raises:
            ValueError: 如果提供商不存在
        """
        if provider_name not in self._providers:
            raise ValueError(f"Provider '{provider_name}' not found. Available: {list(self._providers.keys())}")
        return self._providers[provider_name]

    def create(
        self,
        provider: str,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None
    ) -> BaseLLM:
        """
        创建 LLM 实例

        Args:
            provider: 提供商名称
            api_key: API Key（如果不提供则使用已注册的配置）
            base_url: Base URL（可选）
            model: 模型名称（可选）

        Returns:
            BaseLLM 实例

        Raises:
            ValueError: 如果缺少必要配置
        """
        provider_cls = self.get_provider(provider)

        if not api_key:
            if provider not in self._configs:
                raise ValueError(f"No config registered for provider '{provider}'. "
                                 f"Please provide api_key or register a config first.")
            config = self._configs[provider]
            api_key = config.api_key
            base_url = base_url or config.base_url
            model = model or config.model

        return provider_cls(api_key=api_key, base_url=base_url, model=model)

    def list_providers(self) -> List[dict]:
        """
        列出所有已注册的提供商

        Returns:
            提供商信息列表
        """
        return [
            {
                "name": cls.name,
                "default_model": cls.default_model,
                "supported_models": cls.supported_models
            }
            for cls in self._providers.values()
        ]


llm_factory = LLMFactory()

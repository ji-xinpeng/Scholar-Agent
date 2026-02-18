from abc import ABC, abstractmethod
from typing import Dict, Any


class BaseTool(ABC):
    """工具基类"""
    name: str = ""
    description: str = ""
    parameters: dict = {}

    @abstractmethod
    async def run(self, **kwargs) -> Any:
        """执行工具"""
        pass

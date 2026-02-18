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

    def resolve_params(self, params: Dict[str, Any], previous_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        从之前的结果中解析参数
        
        Args:
            params: 当前工具的参数
            previous_results: 之前工具执行的结果字典，key 为工具名
        
        Returns:
            解析后的完整参数字典
        """
        return params

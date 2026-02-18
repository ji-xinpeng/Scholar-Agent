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
    
    def get_action_label(self, params: Dict[str, Any]) -> str:
        """
        根据参数生成任务展示文案
        
        Args:
            params: 工具参数字典
        
        Returns:
            展示文案
        """
        # 默认实现：取一个代表性参数做预览
        for key in ("query", "content", "filename", "doc_id", "action"):
            val = params.get(key)
            if val is not None and str(val).strip():
                preview = str(val).strip()[:25]
                if len(str(val).strip()) > 25:
                    preview += "…"
                return f"{self.description}: {preview}"
        return self.description

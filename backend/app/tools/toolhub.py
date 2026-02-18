"""
工具中心 (ToolHub)
注册和管理所有可用工具，纯 Python 实现，不依赖 LangChain。
"""
from typing import Dict, Any, Optional, List
from app.tools.base import BaseTool
from app.tools.search.web_search import SearchTool
from app.tools.document.multimodal_parser import MultiModalRAGTool
from app.tools.content.summarizer import SummarizeTool
from app.tools.search.filter import FilterTool
from app.tools.content.citation_generator import CitationTool
from app.tools.document.editor import DocEditTool
from app.tools.user.profile_builder import ProfileTool


class ToolHub:
    """工具注册中心，管理所有可用工具"""

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
        self._register_defaults()

    def _register_defaults(self):
        """注册默认工具"""
        for tool_cls in [SearchTool, MultiModalRAGTool, SummarizeTool, FilterTool, CitationTool, DocEditTool, ProfileTool]:
            tool = tool_cls()
            self._tools[tool.name] = tool

    def register(self, tool: BaseTool):
        """注册自定义工具"""
        self._tools[tool.name] = tool

    def get_tool(self, name: str) -> Optional[BaseTool]:
        """按名称获取工具"""
        return self._tools.get(name)

    def list_tools(self) -> List[Dict[str, Any]]:
        """列出所有已注册的工具，包含参数定义"""
        return [
            {
                "name": t.name,
                "description": t.description,
                "parameters": t.parameters
            } 
            for t in self._tools.values()
        ]

    async def run_tool(self, tool_name: str, **kwargs) -> Optional[Dict[str, Any]]:
        """执行工具，支持灵活参数"""
        tool = self.get_tool(tool_name)
        if tool:
            return await tool.run(**kwargs)
        return None


toolhub = ToolHub()

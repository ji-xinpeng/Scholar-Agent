"""
工具中心 (ToolHub)
注册和管理所有可用工具，纯 Python 实现，不依赖 LangChain。
"""
from typing import Dict, Any, Optional, List
from abc import ABC, abstractmethod
import random
from . import SearchManager


class BaseTool(ABC):
    """工具基类"""
    name: str = ""
    description: str = ""
    parameters: dict = {}

    @abstractmethod
    async def run(self, **kwargs) -> Any:
        """执行工具"""
        pass


class SearchTool(BaseTool):
    name = "SearchTool"
    description = "检索学术论文数据库"
    parameters = {
        "query": {"type": "string", "description": "研究主题关键词", "required": True},
        "max_results": {"type": "integer", "description": "最大返回论文数", "default": 10},
        "year_range": {"type": "string", "description": "年份范围，如 2020-2025", "default": ""}
    }

    async def run(self, **kwargs) -> Dict[str, Any]:
        """搜索学术论文"""
        query = kwargs.get("query", kwargs.get("query") or "")
        max_results = kwargs.get("max_results", 10)
        year_range = kwargs.get("year_range", "")
        
        search_manager = SearchManager()
        results = await search_manager.search([query])
        
        all_papers = []
        for q_result in results.organic:
            for paper in q_result.data:
                paper_dict = paper.model_dump() if hasattr(paper, 'model_dump') else paper.dict()
                all_papers.append(paper_dict)
        
        return {
            "success": True,
            "query": query,
            "max_results": max_results,
            "year_range": year_range,
            "papers_found": len(all_papers),
            "papers": all_papers
        }


class MultiModalRAGTool(BaseTool):
    name = "MultiModalRAGTool"
    description = "基于上传文档进行多模态问答"
    parameters = {
        "query": {"type": "string", "description": "用户问题", "required": True},
        "document_ids": {"type": "array", "description": "指定文档ID列表", "default": []},
        "top_k": {"type": "integer", "description": "返回最相关的 k 个片段", "default": 5}
    }

    async def run(self, **kwargs) -> Dict[str, Any]:
        """基于文档的 RAG 检索"""
        query = kwargs.get("query", "")
        document_ids = kwargs.get("document_ids", [])
        top_k = kwargs.get("top_k", 5)
        
        # TODO: 对接多模态 RAG 检索管线
        return {
            "success": True,
            "query": query,
            "document_ids": document_ids,
            "top_k": top_k,
            "answer": f"这是基于文档的回答：关于 \"{query}\" 的相关内容...",
            "sources": ["document_1.pdf", "document_2.pdf"]
        }


class SummarizeTool(BaseTool):
    name = "SummarizeTool"
    description = "对检索结果进行归纳总结"
    parameters = {
        "content": {"type": "string", "description": "要总结的文本内容", "required": True},
        "max_length": {"type": "integer", "description": "摘要最大长度", "default": 200},
        "style": {"type": "string", "description": "摘要风格：concise/verbose", "default": "concise"}
    }

    async def run(self, **kwargs) -> Dict[str, Any]:
        """生成摘要"""
        content = kwargs.get("content", kwargs.get("query", ""))
        max_length = kwargs.get("max_length", 200)
        style = kwargs.get("style", "concise")
        
        # 这个工具现在主要由 LLM 直接处理，但保留接口
        return {
            "success": True,
            "content": content,
            "max_length": max_length,
            "style": style,
            "summary": f"摘要：{content[:100]}..."
        }


class FilterTool(BaseTool):
    name = "FilterTool"
    description = "筛选与排序检索结果"
    parameters = {
        "papers": {"type": "array", "description": "论文列表", "required": True},
        "sort_by": {"type": "string", "description": "排序字段：citations/year/relevance", "default": "relevance"},
        "min_citations": {"type": "integer", "description": "最小引用数", "default": 0},
        "year_from": {"type": "integer", "description": "起始年份", "default": 2000}
    }

    async def run(self, **kwargs) -> Dict[str, Any]:
        """筛选和排序论文"""
        papers = kwargs.get("papers", [])
        sort_by = kwargs.get("sort_by", "relevance")
        min_citations = kwargs.get("min_citations", 0)
        year_from = kwargs.get("year_from", 2000)
        
        # TODO: 实现基于引用数、相关度的筛选逻辑
        return {
            "success": True,
            "sort_by": sort_by,
            "min_citations": min_citations,
            "year_from": year_from,
            "message": "筛选完成"
        }


class CitationTool(BaseTool):
    name = "CitationTool"
    description = "自动生成引用格式"
    parameters = {
        "papers": {"type": "array", "description": "论文信息列表", "required": True},
        "format": {"type": "string", "description": "引用格式：gb7714/apa/mla", "default": "gb7714"}
    }

    async def run(self, **kwargs) -> Dict[str, Any]:
        """生成引用"""
        papers = kwargs.get("papers", [])
        format = kwargs.get("format", "gb7714")
        
        # 这个工具现在主要由 LLM 直接处理，但保留接口
        return {
            "success": True,
            "papers": papers,
            "format": format,
            "citations": []
        }


class DocTool(BaseTool):
    name = "DocTool"
    description = "文档管理工具"
    parameters = {
        "action": {"type": "string", "description": "操作类型：upload/delete/list", "required": True},
        "file_path": {"type": "string", "description": "文件路径", "default": ""}
    }

    async def run(self, **kwargs) -> Dict[str, Any]:
        """文档操作"""
        action = kwargs.get("action", "")
        file_path = kwargs.get("file_path", kwargs.get("query", ""))
        
        return {
            "success": True,
            "action": action,
            "file_path": file_path,
            "result": f"文档操作已完成: {action} {file_path}"
        }


class ProfileTool(BaseTool):
    name = "ProfileTool"
    description = "用户画像工具"
    parameters = {
        "user_id": {"type": "string", "description": "用户ID", "default": ""},
        "fields": {"type": "array", "description": "要查询的字段", "default": ["interests", "recent_papers"]}
    }

    async def run(self, **kwargs) -> Dict[str, Any]:
        """用户画像查询"""
        user_id = kwargs.get("user_id", kwargs.get("query", ""))
        fields = kwargs.get("fields", ["interests", "recent_papers"])
        
        return {
            "success": True,
            "user_id": user_id,
            "fields": fields,
            "profile": {
                "interests": ["机器学习", "自然语言处理"],
                "recent_papers": 5
            }
        }


class ToolHub:
    """工具注册中心，管理所有可用工具"""

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
        self._register_defaults()

    def _register_defaults(self):
        """注册默认工具"""
        for tool_cls in [SearchTool, MultiModalRAGTool, SummarizeTool, FilterTool, CitationTool, DocTool, ProfileTool]:
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

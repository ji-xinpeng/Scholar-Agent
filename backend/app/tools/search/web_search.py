from typing import Dict, Any
from app.tools.base import BaseTool
import requests
import json
import asyncio
from typing import Optional, List
from pydantic import BaseModel, Field
from app.infrastructure.logging.config import logger
from app.infrastructure.storage.redis import cache_manager


class ScholarResultItem(BaseModel):
    """单个学术搜索结果"""
    title: Optional[str] = None
    link: Optional[str] = None
    publicationInfo: Optional[str] = None
    snippet: Optional[str] = None
    abstract: Optional[str] = None
    year: Optional[int] = None
    citedBy: Optional[int] = None
    pdfUrl: Optional[str] = None
    htmlUrl: Optional[str] = None
    id: Optional[str] = None


class ScholarQueryResult(BaseModel):
    """单次查询的搜索结果"""
    query: str
    page: int
    data: List[ScholarResultItem] = Field(default_factory=list)


class ScholarSearchResult(BaseModel):
    """学术搜索结果（包含多个查询的结果）"""
    organic: List[ScholarQueryResult] = Field(default_factory=list)


class SearchManager:
    """
    搜索学术论文
    """
    def __init__(self):
        self.api_key = "d6fe663fc23ca5ec5f35a0413af31ab21286949f"
        self.scholar_url = "https://google.serper.dev/scholar"
        self.headers = {
            'X-API-KEY': self.api_key,
            'Content-Type': 'application/json'
        }


    async def _scholar_search(self, query: str, page: int = 1) -> List[ScholarResultItem]:
        """搜索学术论文"""
        payload = json.dumps({
            "q": query,
            "page": page
        })
        response = requests.request("POST", self.scholar_url, headers=self.headers, data=payload)
        result = response.json()
        if not result["organic"]:
            return []
        
        items = []
        for item in result["organic"]:
            try:
                scholar_item = ScholarResultItem(**item)
                items.append(scholar_item)
            except Exception as e:
                logger.warning(f"Failed to parse item: {e}")
                continue
        return items


    async def search(self, search_queries: List[str], page: int = 1) -> ScholarSearchResult:
        """并行搜索"""
        tasks = [self._scholar_search(query, page) for query in search_queries]
        
        results_list = await asyncio.gather(*tasks)
        
        query_results = []
        for query, result in zip(search_queries, results_list):
            query_result = ScholarQueryResult(query=query, page=page, data=result)
            query_results.append(query_result)
        
        return ScholarSearchResult(organic=query_results)


class SearchTool(BaseTool):
    name = "SearchTool"
    description = "检索学术论文数据库，返回论文列表。支持根据用户研究领域和知识水平进行个性化搜索。结果可被后续的 FilterTool 或 CitationTool 直接使用。"
    parameters = {
        "query": {"type": "string", "description": "研究主题关键词", "required": True},
        "max_results": {"type": "integer", "description": "最大返回论文数", "default": 10},
        "year_range": {"type": "string", "description": "年份范围，如 2020-2025", "default": ""},
        "user_id": {"type": "string", "description": "用户ID，用于个性化搜索", "default": ""}
    }

    async def run(self, **kwargs) -> Dict[str, Any]:
        """搜索学术论文（简化版）"""
        query = kwargs.get("query", kwargs.get("query") or "")
        max_results = kwargs.get("max_results", 10)
        year_range = kwargs.get("year_range", "")
        user_id = kwargs.get("user_id", "")
        
        # 获取用户资料用于个性化搜索
        user_profile = None
        if user_id:
            try:
                from app.application.services.user_service import user_service
                user_profile = user_service.get_profile(user_id)
                logger.info(f"SearchTool 获取到用户资料: user_id={user_id}, research_field={user_profile.get('research_field')}")
            except Exception as e:
                logger.warning(f"SearchTool 获取用户资料失败: {e}")
        
        # 构建增强的查询
        enhanced_query = query
        if user_profile and user_profile.get("research_field"):
            # 如果用户有研究领域，将其添加到搜索词中
            research_field = user_profile["research_field"]
            if research_field not in query:
                enhanced_query = f"{query} {research_field}"
                logger.info(f"SearchTool 使用增强查询: {enhanced_query}")
        
        # 尝试从缓存获取
        cache_key = f"search:{enhanced_query}:{max_results}:{year_range}:{user_id}"
        cached_result = cache_manager.get(cache_key)
        if cached_result is not None:
            logger.info(f"SearchTool 缓存命中: {enhanced_query}")
            return cached_result

        search_manager = SearchManager()
        search_results = await search_manager.search([enhanced_query], max_results)
        papers = []
        if search_results.organic:
            papers = [paper.model_dump() for paper in search_results.organic[0].data]
        
        result = {
            "success": True,
            "papers": papers,
            "original_query": query,
            "enhanced_query": enhanced_query,
            "user_profile_used": user_profile is not None
        }

        # 缓存结果（缓存 24 小时）
        cache_manager.set(cache_key, result, ttl=86400)
        return result
    
    def resolve_params(self, params: Dict[str, Any], previous_results: Dict[str, Any]) -> Dict[str, Any]:
        """自动解析参数"""
        return params
from typing import Dict, Any
from app.tools.base import BaseTool
import json
import asyncio
import aiohttp
from typing import Optional, List
from pydantic import BaseModel, Field
from app.infrastructure.logging.config import logger
from app.infrastructure.storage.redis import cache_manager
from app.infrastructure.llm.service import llm_service, ChatMessage, MessageRole


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


class OptimizedSearchQueries(BaseModel):
    """优化后的搜索查询"""
    original_query: str
    optimized_queries: List[str] = Field(..., description="3-5个优化后的学术搜索查询，每个查询都是独立的关键词组合")


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
        """异步搜索学术论文"""
        payload = {
            "q": query,
            "page": page
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.scholar_url,
                    headers=self.headers,
                    json=payload,
                    timeout=30
                ) as response:
                    result = await response.json()
                    if not result.get("organic"):
                        logger.info(f"Search query '{query}' 返回空结果")
                        return []
                    
                    items = []
                    for item in result["organic"]:
                        try:
                            scholar_item = ScholarResultItem(**item)
                            items.append(scholar_item)
                        except Exception as e:
                            logger.warning(f"Failed to parse item: {e}")
                            continue
                    logger.info(f"Search query '{query}' 找到 {len(items)} 篇论文")
                    return items
        except Exception as e:
            logger.error(f"Search query '{query}' 失败: {e}", exc_info=True)
            return []


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

    async def _optimize_query(self, query: str, user_profile: Optional[Dict] = None) -> List[str]:
        """使用 LLM 优化搜索查询"""
        system_prompt = """你是一位学术搜索专家。请将用户的研究需求改写为 3-5 个不同的学术搜索查询。

        要求：
        1. 每个查询都是独立的关键词组合，用英文
        2. 适合在 Google Scholar 等学术搜索引擎中搜索
        3. 覆盖不同的表达方式和角度
        4. 直接返回 JSON 格式，不要有其他文字
        5. 每个查询简洁明了，不超过 10 个词

        返回格式：
        {
        "original_query": "原始查询",
        "optimized_queries": ["查询1", "查询2", "查询3", "查询4", "查询5"]
        }"""    

        user_prompt = f"原始查询: {query}"
        if user_profile and user_profile.get("research_field"):
            user_prompt += f"\n用户研究领域: {user_profile['research_field']}"
        if user_profile and user_profile.get("knowledge_level"):
            user_prompt += f"\n用户知识水平: {user_profile['knowledge_level']}"

        try:
            messages = [
                ChatMessage(role=MessageRole.SYSTEM, content=system_prompt),
                ChatMessage(role=MessageRole.USER, content=user_prompt)
            ]
            response = await llm_service.chat(messages, response_format=OptimizedSearchQueries, temperature=0.7)
            if response.parsed:
                logger.info(f"SearchTool 查询优化结果: {response.parsed.optimized_queries}")
                return response.parsed.optimized_queries
        except Exception as e:
            logger.warning(f"SearchTool 查询优化失败: {e}")
        
        return [query]

    async def run(self, **kwargs) -> Dict[str, Any]:
        """搜索学术论文（改进版，含查询优化）"""
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
        
        # 优化查询
        optimized_queries = await self._optimize_query(query, user_profile)
        logger.info(f"SearchTool 原始查询: {query}")
        logger.info(f"SearchTool 优化后查询: {optimized_queries}")
        
        # 尝试从缓存获取
        cache_key = f"search:{query}:{max_results}:{year_range}:{user_id}"
        cached_result = cache_manager.get(cache_key)
        if cached_result is not None:
            logger.info(f"SearchTool 缓存命中: {query}")
            return cached_result

        # 并行搜索所有优化后的查询
        search_manager = SearchManager()
        search_results = await search_manager.search(optimized_queries, max_results)
        
        # 合并所有查询结果并去重（基于标题）
        all_papers = []
        seen_titles = set()
        for query_result in search_results.organic:
            for paper in query_result.data:
                if paper.title and paper.title not in seen_titles:
                    seen_titles.add(paper.title)
                    all_papers.append(paper.model_dump())
        
        # 限制返回数量
        papers = all_papers[:max_results]
        
        # 构建友好的展示信息
        query_info = f"原始查询: {query}\n"
        query_info += "优化后的搜索词:\n"
        for i, q in enumerate(optimized_queries, 1):
            query_info += f"  {i}. {q}\n"
        
        result = {
            "success": True,
            "papers": papers,
            "original_query": query,
            "optimized_queries": optimized_queries,
            "query_info": query_info,
            "total_found": len(all_papers),
            "user_profile_used": user_profile is not None
        }

        # 缓存结果（缓存 24 小时）
        cache_manager.set(cache_key, result, ttl=86400)
        return result
    
    def resolve_params(self, params: Dict[str, Any], previous_results: Dict[str, Any]) -> Dict[str, Any]:
        """自动解析参数"""
        return params
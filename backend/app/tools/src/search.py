import requests
import json
import asyncio
from pydantic import BaseModel, Field
from typing import Optional, List

from app.core.logger import logger


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



if __name__ == "__main__":
    search_manager = SearchManager()
    res = asyncio.run(search_manager.search(["machine learning"]))
    print(res)

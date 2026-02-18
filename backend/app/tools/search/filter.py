from typing import Dict, Any, List
from app.tools.base import BaseTool


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
        
        if not papers or not isinstance(papers, list):
            return {
                "success": False,
                "error": "无效的论文列表"
            }

        try:
            filtered_papers = []
            for paper in papers:
                if not isinstance(paper, dict):
                    continue
                    
                cited_by = paper.get("citedBy", paper.get("citations", 0))
                year = paper.get("year", 2000)
                
                if cited_by >= min_citations and year >= year_from:
                    filtered_papers.append(paper)
            
            sorted_papers = filtered_papers.copy()
            if sort_by == "citations":
                sorted_papers.sort(key=lambda x: x.get("citedBy", x.get("citations", 0)), reverse=True)
            elif sort_by == "year":
                sorted_papers.sort(key=lambda x: x.get("year", 0), reverse=True)
            
            return {
                "success": True,
                "papers": sorted_papers,
                "sort_by": sort_by,
                "min_citations": min_citations,
                "year_from": year_from,
                "total_count": len(sorted_papers),
                "message": f"筛选完成，共 {len(sorted_papers)} 篇论文"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"筛选失败: {str(e)}"
            }

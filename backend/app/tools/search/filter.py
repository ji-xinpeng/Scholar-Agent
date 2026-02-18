from typing import Dict, Any, List
from app.tools.base import BaseTool
from app.infrastructure.logging.config import logger


class FilterTool(BaseTool):
    name = "FilterTool"
    description = "筛选与排序检索结果"
    parameters = {
        "papers": {"type": "array", "description": "论文列表（若本步骤紧接在 SearchTool 或 FilterTool 之后，可不传，系统自动使用上一步结果）", "required": True},
        "sort_by": {"type": "string", "description": "排序字段：citations/year/relevance", "default": "relevance"},
        "min_citations": {"type": "integer", "description": "最小引用数", "default": 0},
        "year_from": {"type": "integer", "description": "起始年份", "default": 2000}
    }

    def resolve_params(self, params: Dict[str, Any], previous_results: Dict[str, Any]) -> Dict[str, Any]:
        params = dict(params) if params else {}
        if not params.get("papers") or params.get("papers") == []:
            for prev_tool in ("FilterTool", "SearchTool"):
                if prev_tool in previous_results:
                    prev_result = previous_results[prev_tool]
                    if isinstance(prev_result, dict) and prev_result.get("success"):
                        papers = prev_result.get("papers")
                        if isinstance(papers, list) and papers:
                            params["papers"] = papers
                            logger.info(f"{self.name} 自动使用 {prev_tool} 的结果（{len(papers)} 篇论文）")
                            break
        return params

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

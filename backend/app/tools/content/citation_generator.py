from typing import Dict, Any, List
from app.tools.base import BaseTool
from app.infrastructure.logging.config import logger


class CitationTool(BaseTool):
    name = "CitationTool"
    description = "自动生成引用格式"
    parameters = {
        "papers": {"type": "array", "description": "论文信息列表（若本步骤紧接在 SearchTool 或 FilterTool 之后，可不传，系统自动使用上一步结果）", "required": True},
        "format": {"type": "string", "description": "引用格式：gb7714/apa/mla", "default": "gb7714"}
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

    def _generate_gb7714_citation(self, paper: dict) -> str:
        """生成 GB/T 7714 格式引用"""
        title = paper.get("title", "无标题")
        authors = paper.get("authors", paper.get("publicationInfo", ""))
        year = paper.get("year", "")
        link = paper.get("link", paper.get("htmlUrl", ""))
        
        if authors:
            if isinstance(authors, list):
                authors_str = ", ".join(authors)
            else:
                authors_str = str(authors)
            return f"{authors_str}. {title}[J]. {year}." if year else f"{authors_str}. {title}."
        else:
            return f"{title}[J]. {year}." if year else f"{title}."

    def _generate_apa_citation(self, paper: dict) -> str:
        """生成 APA 格式引用"""
        title = paper.get("title", "无标题")
        authors = paper.get("authors", paper.get("publicationInfo", ""))
        year = paper.get("year", "n.d.")
        
        if authors:
            if isinstance(authors, list):
                authors_str = ", ".join(authors)
            else:
                authors_str = str(authors)
            return f"{authors_str}. ({year}). {title}."
        else:
            return f"{title}. ({year})."

    def _generate_mla_citation(self, paper: dict) -> str:
        """生成 MLA 格式引用"""
        title = paper.get("title", "无标题")
        authors = paper.get("authors", paper.get("publicationInfo", ""))
        year = paper.get("year", "")
        
        if authors:
            if isinstance(authors, list):
                authors_str = ", ".join(authors)
            else:
                authors_str = str(authors)
            return f"{authors_str}. \"{title}\". {year}." if year else f"{authors_str}. \"{title}\"."
        else:
            return f"\"{title}\". {year}." if year else f"\"{title}\"."

    async def run(self, **kwargs) -> Dict[str, Any]:
        """生成引用"""
        papers = kwargs.get("papers", [])
        format = kwargs.get("format", "gb7714")
        
        if not papers or not isinstance(papers, list):
            return {
                "success": False,
                "error": "无效的论文列表"
            }

        try:
            citations = []
            for paper in papers:
                if not isinstance(paper, dict):
                    continue
                    
                if format == "apa":
                    citation = self._generate_apa_citation(paper)
                elif format == "mla":
                    citation = self._generate_mla_citation(paper)
                else:
                    citation = self._generate_gb7714_citation(paper)
                    
                citations.append({
                    "paper": paper,
                    "citation": citation
                })
            
            return {
                "success": True,
                "papers": papers,
                "format": format,
                "citations": citations,
                "total_count": len(citations),
                "message": f"成功生成 {len(citations)} 条引用"
            }
        except Exception as e:
            logger.error(f"CitationTool 执行失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"引用生成失败: {str(e)}"
            }

from typing import Dict, Any, List
from app.tools.base import BaseTool


class CitationTool(BaseTool):
    name = "CitationTool"
    description = "自动生成引用格式"
    parameters = {
        "papers": {"type": "array", "description": "论文信息列表", "required": True},
        "format": {"type": "string", "description": "引用格式：gb7714/apa/mla", "default": "gb7714"}
    }

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
            return {
                "success": False,
                "error": f"引用生成失败: {str(e)}"
            }

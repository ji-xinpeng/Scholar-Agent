from typing import Dict, Any
from app.tools.base import BaseTool
from app.infrastructure.llm.base import MessageRole, ChatMessage
from app.infrastructure.llm.service import llm_service
from app.infrastructure.logging.config import logger


class SummarizeTool(BaseTool):
    name = "SummarizeTool"
    description = "对检索结果进行归纳总结。若紧接在 SearchTool 或 FilterTool 之后，可自动使用其结果。"
    parameters = {
        "content": {"type": "string", "description": "要总结的文本内容（可选，若前面有 SearchTool/FilterTool 结果可自动获取）", "required": False},
        "papers": {"type": "array", "description": "论文列表（可选，优先级高于 content）", "required": False},
        "max_length": {"type": "integer", "description": "摘要最大长度", "default": 500},
        "style": {"type": "string", "description": "摘要风格：concise/verbose", "default": "concise"}
    }

    def resolve_params(self, params: Dict[str, Any], previous_results: Dict[str, Any]) -> Dict[str, Any]:
        params = dict(params) if params else {}
        # 如果有 papers 或 content 参数，直接使用
        if params.get("papers") or params.get("content"):
            return params
        
        # 尝试从之前的工具结果中获取
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
        """生成摘要"""
        papers = kwargs.get("papers", [])
        content = kwargs.get("content", "")
        max_length = kwargs.get("max_length", 500)
        style = kwargs.get("style", "concise")
        
        # 优先从 papers 生成内容
        if papers and isinstance(papers, list):
            content_parts = []
            for i, paper in enumerate(papers[:10], 1):  # 最多取 10 篇
                title = paper.get("title", "无标题")
                abstract = paper.get("abstract", "")
                authors = paper.get("authors", "")
                year = paper.get("year", "")
                cited_by = paper.get("citedBy", paper.get("citations", 0))
                
                part = f"[{i}] {title}"
                if authors:
                    part += f"\n作者: {authors}"
                if year:
                    part += f"\n年份: {year}"
                if cited_by:
                    part += f"\n引用: {cited_by}"
                if abstract:
                    part += f"\n摘要: {abstract}"
                content_parts.append(part)
            
            content = "\n\n".join(content_parts)
        
        if not content:
            return {"success": False, "error": "没有内容可以总结"}

        try:
            style_desc = "简洁" if style == "concise" else "详细"
            prompt = f"""请对以下内容进行{style_desc}的综合总结，不超过{max_length}字：
            {content}
            """

            messages = [ChatMessage(role=MessageRole.USER, content=prompt)]
            response = await llm_service.chat(messages, temperature=0.3, max_tokens=max_length * 2)
            
            return {
                "success": True,
                "content": content,
                "max_length": max_length,
                "style": style,
                "summary": response.content
            }
        except Exception as e:
            logger.error(f"SummarizeTool 执行失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"摘要生成失败: {str(e)}"
            }

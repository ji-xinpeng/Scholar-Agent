from typing import Dict, Any
from app.tools.base import BaseTool
from app.infrastructure.llm.service import MessageRole, ChatMessage, llm_service
from app.infrastructure.logging.config import logger


class SummarizeTool(BaseTool):
    name = "SummarizeTool"
    description = "对检索结果进行归纳总结。支持根据用户知识水平调整总结深度和风格。若紧接在 SearchTool 或 FilterTool 之后，可自动使用其结果。"
    parameters = {
        "content": {"type": "string", "description": "要总结的文本内容（可选，若前面有 SearchTool/FilterTool 结果可自动获取）", "required": False},
        "papers": {"type": "array", "description": "论文列表（可选，优先级高于 content）", "required": False},
        "max_length": {"type": "integer", "description": "摘要最大长度", "default": 500},
        "style": {"type": "string", "description": "摘要风格：concise/verbose", "default": "concise"},
        "user_id": {"type": "string", "description": "用户ID，用于根据用户知识水平调整总结深度", "default": ""}
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
        user_id = kwargs.get("user_id", "")
        
        # 获取用户资料用于个性化总结
        user_profile = None
        knowledge_level = "intermediate"
        research_field = ""
        if user_id:
            try:
                from app.application.services.user_service import user_service
                user_profile = user_service.get_profile(user_id)
                knowledge_level = user_profile.get("knowledge_level", "intermediate")
                research_field = user_profile.get("research_field", "")
                logger.info(f"SummarizeTool 获取到用户资料: user_id={user_id}, knowledge_level={knowledge_level}")
            except Exception as e:
                logger.warning(f"SummarizeTool 获取用户资料失败: {e}")
        
        # 根据知识水平调整总结参数
        if knowledge_level == "beginner":
            # 初学者：更详细的解释，更长的总结，通俗易懂的语言
            if max_length == 500:
                max_length = 1000
            style = "verbose"
            logger.info(f"SummarizeTool 应用初学者策略: max_length={max_length}, style={style}")
        elif knowledge_level == "advanced":
            # 高级用户：更简洁，技术性更强
            if max_length == 500:
                max_length = 400
            style = "concise"
            logger.info(f"SummarizeTool 应用高级用户策略: max_length={max_length}, style={style}")
        
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
            
            # 根据知识水平构建不同的提示词
            if knowledge_level == "beginner":
                knowledge_desc = "请用通俗易懂的语言解释，避免使用复杂术语，多举例子"
            elif knowledge_level == "advanced":
                knowledge_desc = "请使用专业术语，重点突出技术创新和方法论"
            else:
                knowledge_desc = ""
            
            prompt = f"""请对以下内容进行{style_desc}的综合总结，不超过{max_length}字。{knowledge_desc}
            {content}
            """

            messages = [ChatMessage(role=MessageRole.USER, content=prompt)]
            response = await llm_service.chat(messages, temperature=0.3, max_tokens=max_length * 2)
            
            return {
                "success": True,
                "content": content,
                "max_length": max_length,
                "style": style,
                "knowledge_level": knowledge_level,
                "user_profile_used": user_profile is not None,
                "summary": response.content
            }
        except Exception as e:
            logger.error(f"SummarizeTool 执行失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"摘要生成失败: {str(e)}"
            }

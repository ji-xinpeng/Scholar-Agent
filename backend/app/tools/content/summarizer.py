from typing import Dict, Any
from app.tools.base import BaseTool
from app.infrastructure.llm.base import MessageRole, ChatMessage
from app.infrastructure.llm.service import llm_service


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
        
        if not content:
            return {"success": False, "error": "没有内容可以总结"}

        try:
            style_desc = "简洁" if style == "concise" else "详细"
            prompt = f"""请对以下内容进行{style_desc}摘要，不超过{max_length}字：

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
            return {
                "success": False,
                "error": f"摘要生成失败: {str(e)}"
            }

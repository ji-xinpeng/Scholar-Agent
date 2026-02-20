"""
调用大模型工具 (LLMCallTool)
让 Agent 在中间某一步显式调用大模型生成内容，结果作为 observation 供后续推理使用。
"""
from typing import Dict, Any
from app.tools.base import BaseTool
from app.infrastructure.llm.service import MessageRole, ChatMessage, llm_service
from app.infrastructure.logging.config import logger


class LLMCallTool(BaseTool):
    name = "LLMCallTool"
    description = "直接调用大模型完成一段文本生成任务（如解释概念、写摘要、扩写、翻译等）。当需要「让模型自由生成一段内容」且不适合用其他专用工具时使用。"
    parameters = {
        "prompt": {"type": "string", "description": "要让大模型完成的任务或问题（必填）", "required": True},
        "system_prompt": {"type": "string", "description": "可选的系统指令，用于设定角色或格式", "required": False},
        "temperature": {"type": "number", "description": "生成随机性 0~1，默认 0.7", "required": False},
        "max_tokens": {"type": "integer", "description": "最大生成 token 数", "required": False},
    }

    def get_action_label(self, params: Dict[str, Any]) -> str:
        prompt = (params.get("prompt") or "").strip()
        if prompt:
            preview = prompt[:30] + "…" if len(prompt) > 30 else prompt
            return f"调用大模型: {preview}"
        return "调用大模型"

    async def run(self, **kwargs) -> Dict[str, Any]:
        prompt = (kwargs.get("prompt") or "").strip()
        if not prompt:
            return {"success": False, "error": "prompt 不能为空"}

        system_prompt = (kwargs.get("system_prompt") or "").strip()
        temperature = kwargs.get("temperature")
        if temperature is None:
            temperature = 0.7
        max_tokens = kwargs.get("max_tokens")

        messages = []
        if system_prompt:
            messages.append(ChatMessage(role=MessageRole.SYSTEM, content=system_prompt))
        messages.append(ChatMessage(role=MessageRole.USER, content=prompt))

        try:
            chat_kwargs = {"temperature": temperature}
            if max_tokens is not None:
                chat_kwargs["max_tokens"] = max_tokens
            response = await llm_service.chat(messages, **chat_kwargs)
            content = (response.content or "").strip()
            logger.info(f"LLMCallTool 生成长度: {len(content)}")
            return {
                "success": True,
                "prompt": prompt,
                "content": content,
                "message": content,
            }
        except Exception as e:
            logger.error(f"LLMCallTool 执行失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "prompt": prompt,
            }

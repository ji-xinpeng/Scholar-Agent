import json
import asyncio
import uuid
import random
from datetime import datetime, timezone
from typing import AsyncGenerator, Dict, Any
from app.infrastructure.logging.config import logger
from app.infrastructure.llm.base import MessageRole, ChatMessage
from app.infrastructure.llm.service import llm_service
from app.tools.hub import toolhub
from app.application.services.document_service import document_service
from app.application.services.session_service import session_service


class AgentOrchestrator:
    """Agent 编排引擎 - 负责协调和执行聊天流程"""

    def _sse(self, event_type: str, data: dict) -> str:
        data["timestamp"] = datetime.now(timezone.utc).isoformat()
        return f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

    async def run_normal_chat(
        self,
        session_id: str,
        user_id: str,
        user_query: str,
        selected_doc_ids: list = None,
        system_prompt: str = None,
        enable_search: bool = True
    ) -> AsyncGenerator[str, None]:
        """运行普通聊天模式 - 逐步简化以提升稳定性"""
        try:
            selected_doc_ids = selected_doc_ids or []

            metadata = {"document_ids": selected_doc_ids} if selected_doc_ids else None
            user_msg = session_service.add_message(session_id, "user", user_query, "text", metadata=metadata)
            yield self._sse("user_message", user_msg)

            history = session_service.get_messages(session_id)
            messages = self._build_chat_messages(history, system_prompt)

            # 简单 LLM 调用，不使用复杂功能
            yield self._sse("thinking", {"message": "正在思考..."})

            full_response = ""
            async for chunk in llm_service.chat_stream(messages):
                full_response += chunk
                yield self._sse("stream", {"content": chunk})

            assistant_msg = session_service.add_message(session_id, "assistant", full_response, "text")
            yield self._sse("assistant_message", assistant_msg)
            yield self._sse("done", {})

        except Exception as e:
            logger.error(f"聊天错误: {e}", exc_info=True)
            yield self._sse("error", {"message": str(e)})
            yield self._sse("done", {})

    async def run_scholar_chat(
        self,
        session_id: str,
        user_id: str,
        user_query: str,
        selected_doc_ids: list = None,
        system_prompt: str = None
    ) -> AsyncGenerator[str, None]:
        """学者模式 - 保留工具调用但增强稳定性"""
        try:
            selected_doc_ids = selected_doc_ids or []

            metadata = {"document_ids": selected_doc_ids} if selected_doc_ids else None
            user_msg = session_service.add_message(session_id, "user", user_query, "text", metadata=metadata)
            yield self._sse("user_message", user_msg)

            history = session_service.get_messages(session_id)
            base_messages = self._build_chat_messages(history, system_prompt)

            yield self._sse("thinking", {"message": "正在分析问题..."})
            plan = await self._plan_tasks(user_query, base_messages, selected_doc_ids)
            tasks = plan.get("tasks", [])

            # 前端需要 plan 为 [{id, action}] 数组及 thought，至少保留一个步骤避免卡片消失
            plan_steps = [
                {"id": str(i), "action": self._task_action_label(task), "tool_name": task.get("tool"), "params": task.get("params", {})}
                for i, task in enumerate(tasks)
            ]
            if not plan_steps:
                plan_steps = [{"id": "0", "action": "生成回答"}]
            yield self._sse("plan", {"plan": plan_steps, "thought": "已制定执行计划。"})

            results = {}
            for i, task in enumerate(tasks):
                tool_name = task.get("tool")
                params = task.get("params", {})
                step_id = str(i)
                action_label = self._task_action_label(task)

                yield self._sse("step_start", {"step_id": step_id, "action": action_label, "tool_name": tool_name, "params": params})
                tool_result = await toolhub.run_tool(tool_name, **params)
                results[tool_name] = tool_result
                thought_summary = self._result_summary(tool_name, tool_result)
                yield self._sse("step_complete", {"step_id": step_id, "result": tool_result, "thought_summary": thought_summary, "tool_name": tool_name, "params": params})

            # 无工具任务时，标记「生成回答」步骤开始
            if not tasks:
                yield self._sse("step_start", {"step_id": "0", "action": "生成回答"})
            yield self._sse("thinking", {"message": "正在生成回答..."})
            messages_with_results = base_messages + [
                ChatMessage(role=MessageRole.USER, content=f"Context: {json.dumps(results, ensure_ascii=False)}")
            ]

            full_response = ""
            async for chunk in llm_service.chat_stream(messages_with_results):
                full_response += chunk
                yield self._sse("stream", {"content": chunk})

            # 无工具任务时，标记「生成回答」步骤完成
            if not tasks:
                yield self._sse("step_complete", {"step_id": "0", "result": {}, "thought_summary": "回答已生成。"})
            assistant_msg = session_service.add_message(session_id, "assistant", full_response, "text", {"tools_used": list(results.keys())})
            yield self._sse("assistant_message", assistant_msg)
            yield self._sse("done", {})

        except Exception as e:
            logger.error(f"学者模式错误: {e}", exc_info=True)
            yield self._sse("error", {"message": str(e)})
            yield self._sse("done", {})

    async def _plan_tasks(self, query: str, messages: list, selected_doc_ids: list = None) -> dict:
        """任务规划：支持 SearchTool 与 DocEditTool"""
        selected_doc_ids = selected_doc_ids or []
        tasks = []

        # 1. 文档编辑意图：用户选中了文档且表达修改/编辑意图
        edit_keywords = ["修改", "编辑", "更新", "追加", "替换", "改成", "添加", "删除", "改写", "写入"]
        has_edit_intent = any(kw in query for kw in edit_keywords)

        if has_edit_intent and selected_doc_ids:
            doc_id = selected_doc_ids[0]
            edit_plan = await self._plan_doc_edit(query, doc_id)
            if edit_plan:
                tasks.append(edit_plan)

        # 2. 搜索意图：若尚未规划文档编辑，再判断是否需要搜索
        if not tasks:
            plan_prompt = f"用户问题: {query}\n请判断是否需要使用搜索工具查找论文或文献。只需回答：需要 或 不需要。"
            plan_messages = messages + [ChatMessage(role=MessageRole.USER, content=plan_prompt)]
            try:
                response = await llm_service.chat(plan_messages)
                if any(kw in response.content for kw in ["搜索", "查找", "论文", "文献", "需要"]):
                    if "不需要" not in response.content and "无需" not in response.content:
                        tasks.append({
                            "tool": "SearchTool",
                            "params": {"query": query, "max_results": 5}
                        })
            except Exception as e:
                logger.warning(f"搜索规划失败: {e}")

        return {"tasks": tasks}

    async def _plan_doc_edit(self, query: str, doc_id: str) -> dict:
        """规划文档编辑任务：由 LLM 推断 action 及参数"""
        prompt = f"""用户请求: {query}
需编辑的文档ID: {doc_id}

请以 JSON 输出 DocEditTool 的参数，仅输出 JSON，不要其他文字。
- action 必填，取其一: read（仅读取）, update（全文替换）, append（末尾追加）, replace（替换片段）
- doc_id 固定为: {doc_id}
- update/append 时提供 content
- replace 时提供 old_text 和 new_text

示例1 追加: {{"action":"append","doc_id":"{doc_id}","content":"要追加的内容"}}
示例2 替换: {{"action":"replace","doc_id":"{doc_id}","old_text":"原文","new_text":"新文"}}
示例3 读取: {{"action":"read","doc_id":"{doc_id}"}}
"""
        try:
            response = await llm_service.chat([ChatMessage(role=MessageRole.USER, content=prompt)])
            text = response.content.strip()
            obj = None
            # 尝试解析 JSON（可能被 markdown 包裹）
            if "```" in text:
                for block in text.split("```"):
                    block = block.strip()
                    if block.startswith("json"):
                        block = block[4:].strip()
                    if block.startswith("{"):
                        try:
                            obj = json.loads(block)
                            break
                        except json.JSONDecodeError:
                            continue
            if obj is None:
                obj = json.loads(text)

            action = (obj.get("action") or "read").lower()
            params = {"action": action, "doc_id": doc_id}
            if action in ("update", "append") and "content" in obj:
                params["content"] = str(obj["content"])
            if action == "replace":
                params["old_text"] = str(obj.get("old_text", ""))
                params["new_text"] = str(obj.get("new_text", ""))
            return {"tool": "DocEditTool", "params": params}
        except Exception as e:
            logger.warning(f"文档编辑规划失败: {e}")
            return None

    def _task_action_label(self, task: dict) -> str:
        """生成任务展示文案"""
        tool = task.get("tool", "")
        params = task.get("params", {})
        if tool == "SearchTool":
            return f"执行搜索: {params.get('query', '')[:30]}..."
        if tool == "DocEditTool":
            act = params.get("action", "")
            act_map = {"read": "读取文档", "update": "全文更新", "append": "追加内容", "replace": "替换片段"}
            return act_map.get(act, act) or "编辑文档"
        return tool or "执行任务"

    def _result_summary(self, tool_name: str, result: Any) -> str:
        """从工具结果生成简短总结"""
        if not isinstance(result, dict):
            return str(result)[:100]
        if result.get("success"):
            if tool_name == "SearchTool" and "results" in result:
                n = len(result.get("results", []))
                return f"检索到 {n} 条结果。"
            if tool_name == "DocEditTool":
                return result.get("message", "操作完成。")
        return result.get("error", "执行完成。")[:80]

    def _build_chat_messages(self, history: list, system_prompt: str = None) -> list:
        messages = []
        if system_prompt:
            messages.append(ChatMessage(role=MessageRole.SYSTEM, content=system_prompt))
        for msg in history:
            try:
                role = MessageRole(msg["role"])
                messages.append(ChatMessage(role=role, content=msg["content"]))
            except Exception:
                pass
        return messages


agent_orchestrator = AgentOrchestrator()

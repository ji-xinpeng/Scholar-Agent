import json
import asyncio
import uuid
import random
import re
from datetime import datetime, timezone
from typing import AsyncGenerator, Dict, Any
from app.infrastructure.logging.config import logger
from app.infrastructure.llm.base import MessageRole, ChatMessage
from app.infrastructure.llm.service import llm_service
from app.tools.toolhub import toolhub
from app.application.services.document_service import document_service
from app.application.services.session_service import session_service


class AgentOrchestrator:
    """Agent 编排引擎 - 负责协调和执行聊天流程"""

    def _extract_json(self, text: str) -> Any:
        """
        从文本中提取并解析 JSON，支持以下情况：
        - 纯 JSON
        - 被 ```json ... ``` 包裹的 JSON
        - 被 ``` ... ``` 包裹的 JSON
        - JSON 前后有其他文字
        
        Args:
            text: 包含 JSON 的文本
        
        Returns:
            解析后的 JSON 对象，解析失败返回 None
        """
        text = text.strip()
        if not text:
            return None

        # 尝试直接解析
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # 使用正则提取 JSON 数组或对象
        # 匹配以 [ 或 { 开头，以 ] 或 } 结尾的内容
        json_pattern = r'(\[[\s\S]*\]|\{[\s\S]*\})'
        matches = re.findall(json_pattern, text)
        
        for match in matches:
            try:
                result = json.loads(match)
                return result
            except json.JSONDecodeError:
                continue

        # 如果正则没找到，尝试提取 code block
        if "```" in text:
            blocks = text.split("```")
            # 倒序查找，因为 JSON 通常在后面
            for block in reversed(blocks):
                block = block.strip()
                if not block:
                    continue
                # 跳过语言标记（如 json、javascript 等）
                if "\n" in block:
                    first_line, rest = block.split("\n", 1)
                    if first_line.lower() in ("json", "javascript", "js", "typescript", "ts"):
                        block = rest.strip()
                try:
                    return json.loads(block)
                except json.JSONDecodeError:
                    continue

        logger.warning(f"无法从文本中解析 JSON: {text[:200]}...")
        return None

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

    async def run_agent_chat(
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
            plan = await self._plan_tasks(user_query, base_messages, selected_doc_ids, user_id)
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
            step_thoughts = {}
            for i, task in enumerate(tasks):
                logger.debug(f"处理任务 {i}: {task}")
                tool_name = task.get("tool")
                params = task.get("params", {})
                # 自动从之前任务的结果中填充缺失参数
                params = self._resolve_task_params(tool_name, params, results)
                step_id = str(i)
                action_label = self._task_action_label(task)

                yield self._sse("step_start", {"step_id": step_id, "action": action_label, "tool_name": tool_name, "params": params})
                tool_result = await toolhub.run_tool(tool_name, **params)
                logger.info(f"{tool_name} 执行结果: {tool_result}")
                results[tool_name] = tool_result
                thought_summary = self._result_summary(tool_name, tool_result)
                step_thoughts[step_id] = thought_summary
                yield self._sse("step_complete", {"step_id": step_id, "result": tool_result, "thought_summary": thought_summary, "tool_name": tool_name, "params": params})
                
                # 如果是文档编辑工具，通知前端刷新文档列表
                if tool_name == "DocEditTool" and isinstance(tool_result, dict):
                    action = tool_result.get("action")
                    doc_id = tool_result.get("doc_id")
                    if action in ("create", "update", "append", "replace", "delete"):
                        yield self._sse("doc_updated", {"doc_id": doc_id, "action": action})

            # 无工具任务时，标记「生成回答」步骤开始
            agent_thought = "已制定执行计划。"
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
            
            # 保存任务计划、思考过程等到消息 metadata
            msg_metadata = {
                "tools_used": list(results.keys()),
                "task_plan": plan_steps,
                "agent_thought": agent_thought,
                "step_thoughts": step_thoughts
            }
            assistant_msg = session_service.add_message(session_id, "assistant", full_response, "text", msg_metadata)
            yield self._sse("assistant_message", assistant_msg)
            yield self._sse("done", {})

        except Exception as e:
            logger.error(f"学者模式错误: {e}", exc_info=True)
            yield self._sse("error", {"message": str(e)})
            yield self._sse("done", {})


    async def _plan_tasks(self, query: str, messages: list, selected_doc_ids: list = None, user_id: str = None) -> dict:
        """任务规划：从已支持的工具中由 LLM 选择合适的工具及参数"""
        selected_doc_ids = selected_doc_ids or []
        available_tools = toolhub.list_tools()

        tools_desc = []
        for t in available_tools:
            params_str = json.dumps(t["parameters"], ensure_ascii=False)
            tools_desc.append(f"- {t['name']}: {t['description']}\n  参数定义: {params_str}")

        context_parts = [f"用户问题: {query}"]
        if selected_doc_ids:
            context_parts.append(f"用户当前选中的文档ID列表: {json.dumps(selected_doc_ids, ensure_ascii=False)}（使用 DocEditTool 或 MultiModalRAGTool 时请使用这些 doc_id）")

        plan_prompt = f"""你是一位专业的任务规划专家。请根据用户问题，从可用工具中选择合适的工具组合来完成任务。

        ## 上下文信息
        {chr(10).join(context_parts)}

        ## 可用工具
        {chr(10).join(tools_desc)}

        ## 任务要求
        1. 分析用户问题，选择零个或多个合适的工具
        2. 确定工具执行顺序，构建任务流程
        3. 为每个工具提供必要的参数
        4. 只输出 JSON 数组，不要任何其他文字

        ## 输出格式
        ```json
        [
        {{"tool": "工具名称", "params": {{"参数名": "参数值"}}}},
        ...
        ]
        ```

        ## 重要规则
        1. 若不需要工具（如简单问答、闲聊），输出 `[]`
        2. 工具名必须与「可用工具」列表中的 name 完全一致
        3. DocEditTool 的 doc_id 优先从「用户当前选中的文档ID列表」中选择
        4. 工具可以串联使用，部分工具可自动使用前序工具的结果
        """

        plan_messages = messages + [ChatMessage(role=MessageRole.USER, content=plan_prompt)]
        tasks = []
        raw_tasks = []
        try:
            response = await llm_service.chat(plan_messages)
            text = (response.content or "").strip()
            
            parsed = self._extract_json(text)
            if isinstance(parsed, list):
                raw_tasks = parsed
            else:
                raw_tasks = []

            tool_names = {t["name"] for t in available_tools}
            for item in raw_tasks:
                if not isinstance(item, dict):
                    continue
                tool_name = item.get("tool") or item.get("tool_name")
                params = item.get("params") or item.get("parameters") or {}
                if not tool_name or tool_name not in tool_names:
                    continue
                # 约束：DocEditTool 若用户选中了文档，则 doc_id 使用选中的第一个
                if tool_name == "DocEditTool":
                    params = dict(params)
                    if selected_doc_ids and "doc_id" not in params:
                        params["doc_id"] = selected_doc_ids[0]
                    # 自动填充 user_id
                    if user_id:
                        params["user_id"] = user_id
                tasks.append({"tool": tool_name, "params": params})
        except Exception as e:
            logger.warning(f"任务规划失败: {e}", exc_info=True)

        return {"tasks": tasks}


    def _task_action_label(self, task: dict) -> str:
        """根据工具描述与参数生成通用任务展示文案"""
        tool_name = task.get("tool", "")
        params = task.get("params", {}) or {}
        meta = toolhub.get_tool(tool_name)
        if meta:
            return meta.get_action_label(params)
        return tool_name or "执行任务"


    def _resolve_task_params(self, tool_name: str, params: dict, previous_results: dict) -> dict:
        """从之前任务的结果中自动填充缺失参数"""
        params = dict(params) if params else {}
        tool_meta = toolhub.get_tool(tool_name)
        if not tool_meta:
            return params
        
        return tool_meta.resolve_params(params, previous_results)

    def _result_summary(self, tool_name: str, result: Any) -> str:
        """从工具结果生成简短总结（通用：按常见返回字段推断）"""
        if not isinstance(result, dict):
            return str(result)[:100]
        if not result.get("success"):
            return (result.get("error") or result.get("message") or "执行完成。")[:80]
        # 成功时优先取文案类字段
        for key in ("message", "summary", "answer"):
            val = result.get(key)
            if val is not None and isinstance(val, str) and val.strip():
                return val.strip()[:80]
        # 再按列表类字段生成「共 n 条/项」
        for key in ("papers", "results", "citations", "content"):
            val = result.get(key)
            if isinstance(val, list):
                n = len(val)
                return f"共 {n} 条结果。" if n else "无结果。"
        return "操作完成。"

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

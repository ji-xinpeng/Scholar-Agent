import json
import re
import ast
from datetime import datetime, timezone
from typing import AsyncGenerator, Dict, Any, List, Tuple, Optional

from app.infrastructure.logging.config import logger
from app.infrastructure.llm.service import MessageRole, ChatMessage, llm_service
from app.tools.toolhub import toolhub
from app.application.services.session_service import session_service
from app.application.services.user_service import user_service
from app.application.agent.react_prompt import get_react_system_prompt
from app.application.agent.persona import PERSONA_PROMPT
from app.application.agent.intent_analyzer import intent_analyzer, ChatIntent
from app.application.agent.intent_prompts import get_intent_prompt
from app.core.config import settings


class AgentOrchestrator:
    """
    Agent 编排引擎
    支持三种模式：普通聊天、论文问答、智能体 (ReAct)
    """

    # =========================================================================
    # 公共入口方法
    # =========================================================================

    async def run_unified_chat(
        self,
        session_id: str,
        user_id: str,
        user_query: str,
        selected_doc_ids: list = None,
        system_prompt: str = None,
        llm_provider: str = None,
        llm_model: str = None,
        llm_temperature: float = None,
        llm_max_tokens: int = None,
        llm_top_p: float = None,
        **llm_kwargs
    ) -> AsyncGenerator[str, None]:
        """
        统一聊天入口：自动识别意图并路由到对应模式
        流程：分析意图 -> 选择模型 -> 路由到对应模式
        """
        try:
            selected_doc_ids = selected_doc_ids or []
            has_docs = len(selected_doc_ids) > 0

            yield self._sse("thinking", {"message": "正在分析意图..."})

            intent_result = await intent_analyzer.analyze(user_query, has_selected_docs=has_docs)
            intent = intent_result.intent
            task_type = intent_result.task_type
            logger.info(f"意图识别结果: intent={intent}, task_type={task_type}, Query: {user_query}")

            # 根据任务类型追加意图相关 prompt，使回答更贴合用户需求
            intent_prompt = get_intent_prompt(task_type)
            combined_system_prompt = (intent_prompt + "\n\n" + system_prompt) if (intent_prompt and system_prompt) else (intent_prompt or system_prompt)

            final_model = llm_model or self._get_model_for_intent(intent)
            logger.info(f"意图: {intent}, task_type: {task_type}, 使用模型: {final_model}")

            if intent == ChatIntent.PAPER_QA:
                yield self._sse("thinking", {"message": "已切换至文档问答模式"})
                async for chunk in self.run_paper_qa_chat(
                    session_id, user_id, user_query, selected_doc_ids, combined_system_prompt,
                    final_model, llm_temperature, llm_max_tokens, llm_top_p, **llm_kwargs
                ):
                    yield chunk

            elif intent == ChatIntent.AGENT:
                yield self._sse("thinking", {"message": "任务较复杂，已切换至智能体模式"})
                async for chunk in self.run_agent_chat(
                    session_id, user_id, user_query, selected_doc_ids, combined_system_prompt,
                    final_model, llm_temperature, llm_max_tokens, llm_top_p, **llm_kwargs
                ):
                    yield chunk

            else:
                logger.info(f"简单对话，使用经济模型: {final_model}")
                async for chunk in self.run_normal_chat(
                    session_id, user_id, user_query, selected_doc_ids, combined_system_prompt,
                    enable_search=False, model=final_model
                ):
                    yield chunk

        except Exception as e:
            logger.error(f"统一对话模式错误: {e}", exc_info=True)
            yield self._sse("error", {"message": str(e)})
            yield self._sse("done", {})

    # =========================================================================
    # 三种聊天模式
    # =========================================================================

    async def run_normal_chat(
        self,
        session_id: str,
        user_id: str,
        user_query: str,
        selected_doc_ids: list = None,
        system_prompt: str = None,
        enable_search: bool = True,
        model: str = None
    ) -> AsyncGenerator[str, None]:
        """普通聊天模式：直接与 LLM 对话"""
        try:
            async for chunk in self._add_user_message(session_id, user_query, selected_doc_ids):
                yield chunk

            history = session_service.get_messages(session_id)
            messages = self._build_chat_messages(history, system_prompt)

            yield self._sse("thinking", {"message": "正在思考..."})

            full_response = ""
            async for chunk in llm_service.chat_stream(messages, model=model):
                full_response += chunk
                yield self._sse("stream", {"content": chunk})

            async for chunk in self._add_assistant_message(session_id, full_response):
                yield chunk
            yield self._sse("done", {})

        except Exception as e:
            logger.error(f"聊天错误: {e}", exc_info=True)
            yield self._sse("error", {"message": str(e)})
            yield self._sse("done", {})

    async def run_paper_qa_chat(
        self,
        session_id: str,
        user_id: str,
        user_query: str,
        selected_doc_ids: list = None,
        system_prompt: str = None,
        llm_model: str = None,
        llm_temperature: float = None,
        llm_max_tokens: int = None,
        llm_top_p: float = None,
        **llm_kwargs
    ) -> AsyncGenerator[str, None]:
        """论文问答模式：仅基于已有文档进行问答"""
        try:
            async for chunk in self._add_user_message(session_id, user_query, selected_doc_ids):
                yield chunk

            yield self._sse("thinking", {"message": "正在检索相关文档..."})

            rag_result = await toolhub.run_tool(
                "MultiModalRAGTool",
                query=user_query,
                document_ids=selected_doc_ids or [],
                user_id=user_id,
                extra_system_prompt=system_prompt,
            )

            if not rag_result or not rag_result.get("success"):
                error_msg = rag_result.get("error", "文档检索失败") if rag_result else "文档检索失败"
                yield self._sse("error", {"message": error_msg})
                yield self._sse("done", {})
                return

            full_response = self._format_rag_response(rag_result)

            yield self._sse("thinking", {"message": "正在生成回答..."})

            for chunk in full_response:
                yield self._sse("stream", {"content": chunk})

            yield self._sse("stream", {"content": ""})
            async for chunk in self._add_assistant_message(session_id, full_response):
                yield chunk
            yield self._sse("done", {})

        except Exception as e:
            logger.error(f"论文问答模式错误: {e}", exc_info=True)
            yield self._sse("error", {"message": str(e)})
            yield self._sse("done", {})

    async def run_agent_chat(
        self,
        session_id: str,
        user_id: str,
        user_query: str,
        selected_doc_ids: list = None,
        system_prompt: str = None,
        llm_model: str = None,
        llm_temperature: float = None,
        llm_max_tokens: int = None,
        llm_top_p: float = None,
        max_iterations: int = 10,
        **llm_kwargs
    ) -> AsyncGenerator[str, None]:
        """
        ReAct 模式：思考-行动-观察循环
        1. 思考 (Thought)
        2. 行动 (Action)
        3. 观察 (Observation)
        4. 重复直到得到答案
        """
        try:
            async for chunk in self._add_user_message(session_id, user_query, selected_doc_ids):
                yield chunk

            messages = await self._init_agent_messages(
                user_query, selected_doc_ids, user_id
            )

            state = self._init_agent_state()
            yield self._sse("thinking", {"message": "正在思考..."})

            for iteration in range(1, max_iterations + 1):
                logger.info(f"ReAct 迭代 {iteration}/{max_iterations}")

                chat_kwargs = self._build_chat_kwargs(
                    llm_model, llm_temperature, llm_max_tokens, llm_top_p, llm_kwargs
                )

                full_content = ""
                current_thought = ""
                last_fa_len = 0
                thought_complete = False
                iteration_done = False

                async for chunk in llm_service.chat_stream(messages, **chat_kwargs):
                    full_content += chunk

                    if not thought_complete:
                        thought_match = re.search(r'<thought>(.*?)</thought>', full_content, re.DOTALL)
                        if thought_match:
                            thought_text = thought_match.group(1).strip()
                            if thought_text and thought_text != current_thought:
                                current_thought = thought_text
                                thought_complete = True
                                yield self._sse("thinking", {"message": current_thought})

                    action_match = re.search(r'<action>(.*?)</action>', full_content, re.DOTALL)
                    if action_match:
                        iteration_done = True
                        break

                    fa_match = re.search(r'<final_answer>(.*?)(?:</final_answer>|$)', full_content, re.DOTALL)
                    if fa_match:
                        fa_text = fa_match.group(1)
                        if len(fa_text) > last_fa_len:
                            delta = fa_text[last_fa_len:]
                            last_fa_len = len(fa_text)

                            if last_fa_len - len(delta) == 0:
                                for s in state["plan_steps"]:
                                    if s.get("status") == "pending":
                                        s["status"] = "done"
                                yield self._sse("plan", {"plan": state["plan_steps"], "thought": state["agent_thought"]})

                            yield self._sse("stream", {"content": delta})

                logger.debug(f"LLM 响应 (Streamed): {full_content[:500]}")

                if not full_content:
                    break

                messages.append(ChatMessage(role=MessageRole.ASSISTANT, content=full_content))

                thought = self._extract_xml_tag(full_content, "thought")
                if thought:
                    state["agent_thought"] = thought
                    state["timeline"].append({"type": "thought", "content": thought})
                    logger.info(f"Thought: {thought}")

                final_answer = self._extract_xml_tag(full_content, "final_answer")
                if final_answer:
                    async for chunk in self._finish_agent_chat(
                        session_id, final_answer, state
                    ):
                        yield chunk
                    return

                action_str = self._extract_xml_tag(full_content, "action")
                if action_str:
                    async for chunk in self._execute_tool_action(
                        action_str, session_id, user_id, selected_doc_ids,
                        messages, state
                    ):
                        yield chunk
                else:
                    logger.warning(f"未找到 action 或 final_answer: {full_content}")
                    break

            logger.warning(f"达到最大迭代次数 {max_iterations}")
            yield self._sse("error", {"message": "执行超时，请重试"})
            yield self._sse("done", {})

        except Exception as e:
            logger.error(f"ReAct 模式错误: {e}", exc_info=True)
            yield self._sse("error", {"message": str(e)})
            yield self._sse("done", {})

    # =========================================================================
    # Agent 模式的辅助方法
    # =========================================================================

    async def _init_agent_messages(
        self, user_query: str, selected_doc_ids: list, user_id: str
    ) -> List[ChatMessage]:
        """初始化 Agent 的消息列表"""
        available_tools = toolhub.list_tools()
        tool_list_str = self._format_tools_description(available_tools)
        tool_usage_hints = self._format_tool_usage_hints(available_tools)
        tool_examples = self._format_tool_examples(available_tools)
        user_profile_info = await self._get_user_profile_info(user_id)

        react_system_prompt = get_react_system_prompt(
            tool_list_str, user_profile_info, user_id,
            tool_usage_hints=tool_usage_hints, tool_examples=tool_examples
        )

        messages = [
            ChatMessage(role=MessageRole.SYSTEM, content=react_system_prompt),
            ChatMessage(role=MessageRole.USER, content=f"<question>{user_query}</question>")
        ]

        if selected_doc_ids:
            doc_info = f"\n用户当前选中的文档ID列表: {json.dumps(selected_doc_ids, ensure_ascii=False)}"
            messages.append(ChatMessage(role=MessageRole.USER, content=doc_info))

        return messages

    def _init_agent_state(self) -> Dict[str, Any]:
        """初始化 Agent 状态"""
        return {
            "plan_steps": [],
            "step_thoughts": {},
            "results": {},
            "previous_results": {},
            "agent_thought": "",
            "timeline": []
        }

    async def _execute_tool_action(
        self, action_str: str, session_id: str, user_id: str,
        selected_doc_ids: list, messages: List[ChatMessage], state: Dict
    ):
        """执行工具 Action"""
        logger.info(f"Action: {action_str}")
        try:
            tool_name, params = self._parse_react_action(action_str)

            params = self._resolve_tool_params(
                tool_name, params, selected_doc_ids, user_id, state["previous_results"]
            )

            step_id = str(len(state["plan_steps"]))
            action_label = self._get_action_label(tool_name, params)
            state["plan_steps"].append({
                "id": step_id,
                "action": action_label,
                "tool_name": tool_name,
                "params": params,
                "status": "running"
            })

            yield self._sse("plan", {"plan": state["plan_steps"], "thought": state["agent_thought"]})
            state["timeline"].append({"type": "step_start", "stepId": step_id, "toolName": tool_name, "action": action_label})
            yield self._sse("step_start", {"step_id": step_id, "action": action_label, "tool_name": tool_name, "params": params})

            tool_result = await toolhub.run_tool(tool_name, **params)
            logger.info(f"{tool_name} 执行结果: {tool_result}")
            state["results"][tool_name] = tool_result
            state["previous_results"][tool_name] = tool_result

            for s in state["plan_steps"]:
                if s["id"] == step_id:
                    s["status"] = "done"

            thought_summary = self._result_summary(tool_name, tool_result)
            state["step_thoughts"][step_id] = thought_summary
            state["timeline"].append({"type": "step_done", "stepId": step_id, "result": thought_summary})
            yield self._sse("step_complete", {
                "step_id": step_id,
                "result": tool_result,
                "thought_summary": thought_summary,
                "tool_name": tool_name,
                "params": params
            })

            async for chunk in self._handle_special_tool_result(tool_name, tool_result):
                yield chunk

            obs_msg = f"<observation>{json.dumps(tool_result, ensure_ascii=False)}</observation>"
            messages.append(ChatMessage(role=MessageRole.USER, content=obs_msg))

        except Exception as e:
            logger.error(f"执行工具失败: {e}", exc_info=True)
            error_msg = f"<observation>工具执行错误: {str(e)}</observation>"
            messages.append(ChatMessage(role=MessageRole.USER, content=error_msg))

    async def _finish_agent_chat(
        self, session_id: str, final_answer: str, state: Dict
    ):
        """完成 Agent 对话"""
        logger.info(f"Final Answer: {final_answer[:200]}")

        msg_metadata = {
            "tools_used": list(state["results"].keys()),
            "task_plan": state["plan_steps"],
            "agent_thought": state["agent_thought"],
            "step_thoughts": state["step_thoughts"],
            "timeline": state["timeline"],
        }
        assistant_msg = session_service.add_message(
            session_id, "assistant", final_answer, msg_type="text", metadata=msg_metadata
        )
        yield self._sse("assistant_message", assistant_msg)
        yield self._sse("done", {})

    # =========================================================================
    # 通用辅助方法
    # =========================================================================

    def _sse(self, event_type: str, data: dict) -> str:
        """构建 SSE 事件"""
        data["timestamp"] = datetime.now(timezone.utc).isoformat()
        return f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

    def _get_model_for_intent(self, intent: ChatIntent) -> Optional[str]:
        """根据意图选择模型"""
        if intent == ChatIntent.SIMPLE:
            return settings.SIMPLE_CHAT_MODEL
        if intent == ChatIntent.PAPER_QA:
            return settings.PAPER_QA_MODEL
        if intent == ChatIntent.AGENT:
            return settings.AGENT_MODEL
        return None

    def _build_chat_messages(self, history: list, system_prompt: str = None) -> list:
        """构建聊天消息列表（始终带小研人设）"""
        messages = []
        system_content = PERSONA_PROMPT
        if system_prompt:
            system_content = f"{PERSONA_PROMPT}\n\n{system_prompt}"
        messages.append(ChatMessage(role=MessageRole.SYSTEM, content=system_content))
        for msg in history:
            try:
                role = MessageRole(msg["role"])
                messages.append(ChatMessage(role=role, content=msg["content"]))
            except Exception:
                pass
        return messages

    def _build_chat_kwargs(
        self, llm_model: str, llm_temperature: float,
        llm_max_tokens: int, llm_top_p: float, llm_kwargs: Dict
    ) -> Dict:
        """构建 LLM 调用参数"""
        chat_kwargs = {}
        if llm_model is not None:
            chat_kwargs["model"] = llm_model
        if llm_temperature is not None:
            chat_kwargs["temperature"] = llm_temperature
        if llm_max_tokens is not None:
            chat_kwargs["max_tokens"] = llm_max_tokens
        if llm_top_p is not None:
            chat_kwargs["top_p"] = llm_top_p
        chat_kwargs.update(llm_kwargs)
        return chat_kwargs

    def _format_tools_description(self, available_tools: List[Dict]) -> str:
        """格式化工具描述"""
        tools_desc = []
        for t in available_tools:
            params_str = json.dumps(t["parameters"], ensure_ascii=False)
            tools_desc.append(f"- {t['name']}: {t['description']}\n  参数定义: {params_str}")
        return "\n".join(tools_desc)

    def _format_tool_usage_hints(self, available_tools: List[Dict]) -> str:
        """格式化工具使用提示"""
        hints = []
        for t in available_tools:
            if t.get("usage_hint"):
                hints.append(f"- {t['name']}：{t['usage_hint']}")
        return "\n\n".join(hints) if hints else "暂无特殊使用提示"

    def _format_tool_examples(self, available_tools: List[Dict]) -> str:
        """格式化工具示例"""
        examples = []
        for t in available_tools:
            if t.get("examples"):
                examples.append(f"### {t['name']} 使用示例\n\n{t['examples']}")
        return "\n\n".join(examples) if examples else "暂无示例"

    async def _get_user_profile_info(self, user_id: str) -> str:
        """获取用户资料信息"""
        try:
            profile = user_service.get_profile(user_id)
            user_profile_parts = []
            if profile.get("display_name"):
                user_profile_parts.append(f"- 姓名: {profile['display_name']}")
            if profile.get("research_field"):
                user_profile_parts.append(f"- 研究领域: {profile['research_field']}")
            if profile.get("knowledge_level"):
                knowledge_level_desc = {
                    "beginner": "初学者",
                    "intermediate": "中级",
                    "advanced": "高级"
                }.get(profile["knowledge_level"], profile["knowledge_level"])
                user_profile_parts.append(f"- 知识水平: {knowledge_level_desc}")
            if profile.get("institution"):
                user_profile_parts.append(f"- 机构: {profile['institution']}")
            if profile.get("bio"):
                user_profile_parts.append(f"- 个人简介: {profile['bio']}")

            if user_profile_parts:
                return "\n".join(user_profile_parts)
            return "当前没有用户资料，将使用默认设置。"
        except Exception as e:
            logger.warning(f"获取用户资料失败: {e}")
            return "获取用户资料失败，将使用默认设置。"

    def _format_rag_response(self, rag_result: Dict) -> str:
        """格式化 RAG 响应"""
        answer = rag_result.get("answer", "")
        sources = rag_result.get("sources", [])
        documents_used = rag_result.get("documents_used", 0)

        full_response = answer
        if sources:
            full_response += f"\n\n---\n\n**参考文档 ({documents_used} 篇):**\n"
            for i, source in enumerate(sources, 1):
                full_response += f"{i}. {source}\n"
        return full_response

    def _resolve_tool_params(
        self, tool_name: str, params: Dict, selected_doc_ids: list,
        user_id: str, previous_results: Dict
    ) -> Dict:
        """解析和补充工具参数"""
        if selected_doc_ids and tool_name == "DocEditTool" and "doc_id" not in params:
            params["doc_id"] = selected_doc_ids[0]
        if user_id and tool_name in ("DocEditTool", "PaperDownloadTool", "MultiModalRAGTool", "SearchTool", "FilterTool", "SummarizeTool", "ProfileTool"):
            params["user_id"] = user_id

        tool_meta = toolhub.get_tool(tool_name)
        if tool_meta and hasattr(tool_meta, "resolve_params"):
            params = tool_meta.resolve_params(params, previous_results)
            logger.info(f"{tool_name} 解析后参数: {params}")

        return params

    async def _handle_special_tool_result(self, tool_name: str, tool_result: Any):
        """处理特殊工具结果（如文档更新）"""
        if tool_name == "DocEditTool" and isinstance(tool_result, dict):
            action = tool_result.get("action")
            doc_id = tool_result.get("doc_id")
            if action in ("create", "update", "append", "replace", "delete"):
                yield self._sse("doc_updated", {"doc_id": doc_id, "action": action})
        if tool_name == "PaperDownloadTool" and isinstance(tool_result, dict) and tool_result.get("success"):
            downloaded_docs = tool_result.get("downloaded_docs", [])
            for doc in downloaded_docs:
                doc_id = doc.get("doc_id")
                if doc_id:
                    action = "create" if not doc.get("cached") else "cached"
                    yield self._sse("doc_updated", {"doc_id": doc_id, "action": action})

    async def _add_user_message(
        self, session_id: str, user_query: str, selected_doc_ids: list
    ):
        """添加用户消息"""
        metadata = {"document_ids": selected_doc_ids} if selected_doc_ids else None
        user_msg = session_service.add_message(session_id, "user", user_query, "text", metadata=metadata)
        yield self._sse("user_message", user_msg)

    async def _add_assistant_message(self, session_id: str, content: str):
        """添加助手消息"""
        assistant_msg = session_service.add_message(session_id, "assistant", content, msg_type="text")
        yield self._sse("assistant_message", assistant_msg)

    # =========================================================================
    # 解析工具方法
    # =========================================================================

    def _extract_xml_tag(self, text: str, tag: str) -> str:
        """从文本中提取 XML 标签内容"""
        pattern = rf'<{tag}>(.*?)</{tag}>'
        match = re.search(pattern, text, re.DOTALL)
        if match:
            return match.group(1).strip()
        return ""

    def _parse_react_action(self, action_str: str) -> Tuple[str, Dict[str, Any]]:
        """解析 ReAct 的 action 字符串，返回工具名和参数字典"""
        match = re.match(r'(\w+)\((.*)\)', action_str.strip(), re.DOTALL)
        if not match:
            raise ValueError(f"无法解析 action: {action_str}")

        func_name = match.group(1)
        args_str = match.group(2).strip()

        if not args_str:
            return func_name, {}

        return func_name, self._parse_action_params(args_str)

    def _parse_action_params(self, args_str: str) -> Dict[str, Any]:
        """解析 action 参数字符串"""
        params = {}
        current_arg = ""
        in_string = False
        string_char = None
        i = 0
        paren_depth = 0

        while i < len(args_str):
            char = args_str[i]

            if not in_string:
                if char in ['"', "'"]:
                    in_string = True
                    string_char = char
                    current_arg += char
                elif char == '(':
                    paren_depth += 1
                    current_arg += char
                elif char == ')':
                    paren_depth -= 1
                    current_arg += char
                elif char == ',' and paren_depth == 0:
                    if current_arg.strip():
                        key, value = self._parse_single_param(current_arg.strip())
                        params[key] = value
                    current_arg = ""
                else:
                    current_arg += char
            else:
                current_arg += char
                if char == string_char and (i == 0 or args_str[i-1] != '\\'):
                    in_string = False
                    string_char = None

            i += 1

        if current_arg.strip():
            key, value = self._parse_single_param(current_arg.strip())
            params[key] = value

        return params

    def _parse_single_param(self, arg_str: str) -> Tuple[str, Any]:
        """解析单个参数，如 key=value"""
        if '=' not in arg_str:
            return arg_str.strip(), True

        key, value_str = arg_str.split('=', 1)
        key = key.strip()
        value_str = value_str.strip()

        if (value_str.startswith('"') and value_str.endswith('"')) or \
           (value_str.startswith("'") and value_str.endswith("'")):
            inner_str = value_str[1:-1]
            inner_str = inner_str.replace('\\"', '"').replace("\\'", "'")
            inner_str = inner_str.replace('\\n', '\n').replace('\\t', '\t')
            inner_str = inner_str.replace('\\r', '\r').replace('\\\\', '\\')
            return key, inner_str

        try:
            return key, ast.literal_eval(value_str)
        except (SyntaxError, ValueError):
            return key, value_str

    def _get_action_label(self, tool_name: str, params: dict) -> str:
        """获取工具执行的描述标签"""
        meta = toolhub.get_tool(tool_name)
        if meta:
            return meta.get_action_label(params)
        return tool_name or "执行任务"

    def _result_summary(self, tool_name: str, result: Any) -> str:
        """从工具结果生成简短总结"""
        if not isinstance(result, dict):
            return str(result)[:100]
        if not result.get("success"):
            return (result.get("error") or result.get("message") or "执行完成。")[:80]
        for key in ("message", "summary", "answer"):
            val = result.get(key)
            if val is not None and isinstance(val, str) and val.strip():
                return val.strip()[:80]
        for key in ("papers", "results", "citations", "content"):
            val = result.get(key)
            if isinstance(val, list):
                n = len(val)
                return f"共 {n} 条结果。" if n else "无结果。"
        return "操作完成。"


agent_orchestrator = AgentOrchestrator()

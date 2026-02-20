import json
import asyncio
import re
import ast
from datetime import datetime, timezone
from typing import AsyncGenerator, Dict, Any, List, Tuple, Optional
from app.infrastructure.logging.config import logger
from app.infrastructure.llm.service import MessageRole, ChatMessage, llm_service
from app.tools.toolhub import toolhub
from app.application.services.document_service import document_service
from app.application.services.session_service import session_service
from app.application.services.user_service import user_service
from app.application.agent.react_prompt import get_react_system_prompt
from app.application.agent.intent_analyzer import intent_analyzer, ChatIntent
from app.core.config import settings


class AgentOrchestrator:
    """Agent 编排引擎 - ReAct 模式"""

    def _get_model_for_intent(self, intent: ChatIntent) -> Optional[str]:
        """根据意图返回豆包模型名（仅豆包一种）。"""
        if intent == ChatIntent.SIMPLE:
            return settings.SIMPLE_CHAT_MODEL
        if intent == ChatIntent.PAPER_QA:
            return settings.PAPER_QA_MODEL
        if intent == ChatIntent.AGENT:
            return settings.AGENT_MODEL
        return None

    def _sse(self, event_type: str, data: dict) -> str:
        data["timestamp"] = datetime.now(timezone.utc).isoformat()
        return f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

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
        """智能统一入口：自动识别意图并路由到对应模式"""
        try:
            selected_doc_ids = selected_doc_ids or []
            has_docs = len(selected_doc_ids) > 0

            # 1. 意图分析
            # 先发一个 thinking 事件让用户知道正在处理
            # 注意：如果是极其简单的问题，这个 thinking 可能会一闪而过
            yield self._sse("thinking", {"message": "正在分析意图..."})
            
            intent = await intent_analyzer.analyze(user_query, has_selected_docs=has_docs)
            logger.info(f"意图识别结果: {intent}, Query: {user_query}")
            
            # 2. 根据意图选择模型（如果用户没有指定）
            auto_model = self._get_model_for_intent(intent)
            final_model = llm_model or auto_model
            
            logger.info(f"意图: {intent}, 使用模型: {final_model}")
            
            # 3. 路由分发
            if intent == ChatIntent.PAPER_QA:
                 yield self._sse("thinking", {"message": "已切换至文档问答模式"})
                 async for chunk in self.run_paper_qa_chat(
                     session_id, user_id, user_query, selected_doc_ids, system_prompt,
                     final_model, llm_temperature, llm_max_tokens, llm_top_p, **llm_kwargs
                 ):
                     yield chunk
                 
            elif intent == ChatIntent.AGENT:
                 yield self._sse("thinking", {"message": "任务较复杂，已切换至智能体模式，正在规划..."})
                 async for chunk in self.run_agent_chat(
                     session_id, user_id, user_query, selected_doc_ids, system_prompt,
                     final_model, llm_temperature, llm_max_tokens, llm_top_p, **llm_kwargs
                 ):
                     yield chunk
                 
            else: # Simple
                 logger.info(f"简单对话，使用经济模型: {final_model}")
                 async for chunk in self.run_normal_chat(
                     session_id, user_id, user_query, selected_doc_ids, system_prompt,
                     enable_search=False, 
                     model=final_model
                 ):
                     yield chunk

        except Exception as e:
            logger.error(f"统一对话模式错误: {e}", exc_info=True)
            yield self._sse("error", {"message": str(e)})
            yield self._sse("done", {})

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
        """运行普通聊天模式"""
        try:
            selected_doc_ids = selected_doc_ids or []

            metadata = {"document_ids": selected_doc_ids} if selected_doc_ids else None
            user_msg = session_service.add_message(session_id, "user", user_query, "text", metadata=metadata)
            yield self._sse("user_message", user_msg)

            history = session_service.get_messages(session_id)
            messages = self._build_chat_messages(history, system_prompt)

            yield self._sse("thinking", {"message": "正在思考..."})

            full_response = ""
            async for chunk in llm_service.chat_stream(messages, model=model):
                full_response += chunk
                yield self._sse("stream", {"content": chunk})

            assistant_msg = session_service.add_message(session_id, "assistant", full_response, "text")
            yield self._sse("assistant_message", assistant_msg)
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
        """论文问答模式 - 仅基于已有文档进行问答"""
        try:
            selected_doc_ids = selected_doc_ids or []

            metadata = {"document_ids": selected_doc_ids} if selected_doc_ids else None
            user_msg = session_service.add_message(session_id, "user", user_query, "text", metadata=metadata)
            yield self._sse("user_message", user_msg)

            yield self._sse("thinking", {"message": "正在检索相关文档..."})

            rag_result = await toolhub.run_tool(
                "MultiModalRAGTool",
                query=user_query,
                document_ids=selected_doc_ids,
                user_id=user_id
            )

            if not rag_result or not rag_result.get("success"):
                error_msg = rag_result.get("error", "文档检索失败") if rag_result else "文档检索失败"
                yield self._sse("error", {"message": error_msg})
                yield self._sse("done", {})
                return

            answer = rag_result.get("answer", "")
            sources = rag_result.get("sources", [])
            documents_used = rag_result.get("documents_used", 0)

            full_response = answer
            if sources:
                full_response += f"\n\n---\n\n**参考文档 ({documents_used} 篇):**\n"
                for i, source in enumerate(sources, 1):
                    full_response += f"{i}. {source}\n"

            history = session_service.get_messages(session_id)
            base_messages = self._build_chat_messages(history, system_prompt)

            yield self._sse("thinking", {"message": "正在生成回答..."})

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

            for chunk in full_response:
                yield self._sse("stream", {"content": chunk})

            yield self._sse("stream", {"content": ""})

            assistant_msg = session_service.add_message(session_id, "assistant", full_response, "text")
            yield self._sse("assistant_message", assistant_msg)
            yield self._sse("done", {})

        except Exception as e:
            logger.error(f"论文问答模式错误: {e}", exc_info=True)
            yield self._sse("error", {"message": str(e)})
            yield self._sse("done", {})

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

    def _parse_react_action(self, action_str: str) -> Tuple[str, Dict[str, Any]]:
        """解析 ReAct 的 action 字符串，返回工具名和参数字典"""
        match = re.match(r'(\w+)\((.*)\)', action_str.strip(), re.DOTALL)
        if not match:
            raise ValueError(f"无法解析 action: {action_str}")

        func_name = match.group(1)
        args_str = match.group(2).strip()

        if not args_str:
            return func_name, {}

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
        
        return func_name, params
    
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

    def _extract_xml_tag(self, text: str, tag: str) -> str:
        """从文本中提取 XML 标签内容"""
        pattern = rf'<{tag}>(.*?)</{tag}>'
        match = re.search(pattern, text, re.DOTALL)
        if match:
            return match.group(1).strip()
        return ""

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
        """ReAct 模式 - 思考-行动-观察循环"""
        try:
            selected_doc_ids = selected_doc_ids or []

            metadata = {"document_ids": selected_doc_ids} if selected_doc_ids else None
            user_msg = session_service.add_message(session_id, "user", user_query, "text", metadata=metadata)
            yield self._sse("user_message", user_msg)

            history = session_service.get_messages(session_id)

            available_tools = toolhub.list_tools()
            tools_desc = []
            for t in available_tools:
                params_str = json.dumps(t["parameters"], ensure_ascii=False)
                tools_desc.append(f"- {t['name']}: {t['description']}\n  参数定义: {params_str}")
            tool_list_str = "\n".join(tools_desc)

            # 获取用户资料
            user_profile_info = ""
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
                    user_profile_info = "\n".join(user_profile_parts)
                else:
                    user_profile_info = "当前没有用户资料，将使用默认设置。"
                logger.info(f"获取到用户资料: {user_profile_info}")
            except Exception as e:
                logger.warning(f"获取用户资料失败: {e}")
                user_profile_info = "获取用户资料失败，将使用默认设置。"

            react_system_prompt = get_react_system_prompt(tool_list_str, user_profile_info, user_id)

            messages = [
                ChatMessage(role=MessageRole.SYSTEM, content=react_system_prompt),
                ChatMessage(role=MessageRole.USER, content=f"<question>{user_query}</question>")
            ]

            if selected_doc_ids:
                doc_info = f"\n用户当前选中的文档ID列表: {json.dumps(selected_doc_ids, ensure_ascii=False)}"
                messages.append(ChatMessage(role=MessageRole.USER, content=doc_info))

            plan_steps = []
            step_thoughts = {}
            results = {}
            previous_results = {}
            iteration = 0
            agent_thought = ""

            # ── 规划阶段：让 LLM 先生成完整执行计划 ──
            yield self._sse("thinking", {"message": "正在分析需求，制定执行计划..."})

            plan_chat_kwargs = {}
            if llm_model is not None:
                plan_chat_kwargs["model"] = llm_model

            planning_prompt = (
                f"<question>{user_query}</question>\n\n"
                "请你先分析这个问题，然后制定一个执行计划。\n"
                "用 <thought> 标签描述你的思考，然后用 <plan> 标签输出一个 JSON 数组，每项包含 step（步骤描述）和 tool（要使用的工具名）。\n"
                "如果不需要任何工具，直接回答即可（<thought>+<final_answer>）。\n"
                "示例：\n"
                '<thought>需要先搜索论文，再总结</thought>\n'
                '<plan>[{"step": "搜索相关论文", "tool": "SearchTool"}, {"step": "总结检索结果", "tool": "SummarizeTool"}]</plan>'
            )
            planning_messages = [
                ChatMessage(role=MessageRole.SYSTEM, content=react_system_prompt),
                ChatMessage(role=MessageRole.USER, content=planning_prompt),
            ]
            if selected_doc_ids:
                planning_messages.append(ChatMessage(
                    role=MessageRole.USER,
                    content=f"用户当前选中的文档ID列表: {json.dumps(selected_doc_ids, ensure_ascii=False)}"
                ))

            plan_response = await llm_service.chat(planning_messages, **plan_chat_kwargs)
            plan_content = plan_response.content or ""
            logger.info(f"规划阶段响应: {plan_content[:500]}")

            plan_thought = self._extract_xml_tag(plan_content, "thought")
            if plan_thought:
                agent_thought = plan_thought
                yield self._sse("thinking", {"message": plan_thought})

            # 如果规划阶段直接给出了最终答案
            plan_final = self._extract_xml_tag(plan_content, "final_answer")
            if plan_final:
                if not plan_steps:
                    plan_steps = [{"id": "0", "action": "直接回答", "status": "done"}]
                yield self._sse("plan", {"plan": plan_steps, "thought": agent_thought})

                for chunk in plan_final:
                    yield self._sse("stream", {"content": chunk})

                msg_metadata = {
                    "tools_used": [],
                    "task_plan": plan_steps,
                    "agent_thought": agent_thought,
                    "step_thoughts": step_thoughts,
                }
                assistant_msg = session_service.add_message(session_id, "assistant", plan_final, "text", msg_metadata)
                yield self._sse("assistant_message", assistant_msg)
                yield self._sse("done", {})
                return

            # 解析 <plan> JSON 生成初始计划步骤
            plan_json_str = self._extract_xml_tag(plan_content, "plan")
            if plan_json_str:
                try:
                    raw_plan = json.loads(plan_json_str)
                    if isinstance(raw_plan, list):
                        for idx, item in enumerate(raw_plan):
                            plan_steps.append({
                                "id": str(idx),
                                "action": item.get("step", f"步骤 {idx + 1}"),
                                "tool_name": item.get("tool"),
                                "status": "pending",
                            })
                except (json.JSONDecodeError, TypeError):
                    logger.warning(f"规划 JSON 解析失败: {plan_json_str}")

            if plan_steps:
                yield self._sse("plan", {"plan": plan_steps, "thought": agent_thought})
            else:
                plan_action = self._extract_xml_tag(plan_content, "action")
                if plan_action:
                    plan_steps.append({"id": "0", "action": "执行任务", "status": "pending"})
                    yield self._sse("plan", {"plan": plan_steps, "thought": agent_thought})

            # ── ReAct 执行循环 ──
            while iteration < max_iterations:
                iteration += 1
                logger.info(f"ReAct 迭代 {iteration}/{max_iterations}")

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

                response = await llm_service.chat(messages, **chat_kwargs)
                content = response.content or ""
                logger.debug(f"LLM 响应: {content[:500]}")

                messages.append(ChatMessage(role=MessageRole.ASSISTANT, content=content))

                thought = self._extract_xml_tag(content, "thought")
                if thought:
                    agent_thought = thought
                    logger.info(f"Thought: {thought}")
                    yield self._sse("thinking", {"message": thought})

                final_answer = self._extract_xml_tag(content, "final_answer")
                if final_answer:
                    logger.info(f"Final Answer: {final_answer[:200]}")

                    for s in plan_steps:
                        if s.get("status") == "pending":
                            s["status"] = "done"
                    yield self._sse("plan", {"plan": plan_steps, "thought": agent_thought})

                    full_response = final_answer
                    for chunk in full_response:
                        yield self._sse("stream", {"content": chunk})

                    msg_metadata = {
                        "tools_used": list(results.keys()),
                        "task_plan": plan_steps,
                        "agent_thought": agent_thought,
                        "step_thoughts": step_thoughts
                    }
                    assistant_msg = session_service.add_message(session_id, "assistant", full_response, "text", msg_metadata)
                    yield self._sse("assistant_message", assistant_msg)
                    yield self._sse("done", {})
                    return

                action_str = self._extract_xml_tag(content, "action")
                if action_str:
                    logger.info(f"Action: {action_str}")
                    try:
                        tool_name, params = self._parse_react_action(action_str)

                        if selected_doc_ids and tool_name == "DocEditTool" and "doc_id" not in params:
                            params["doc_id"] = selected_doc_ids[0]
                        if user_id and tool_name in ("DocEditTool", "PaperDownloadTool", "MultiModalRAGTool", "SearchTool", "FilterTool", "SummarizeTool", "ProfileTool"):
                            params["user_id"] = user_id

                        tool_meta = toolhub.get_tool(tool_name)
                        if tool_meta and hasattr(tool_meta, "resolve_params"):
                            params = tool_meta.resolve_params(params, previous_results)
                            logger.info(f"{tool_name} 解析后参数: {params}")

                        # 匹配或新增计划步骤
                        matched_step = None
                        for s in plan_steps:
                            if s.get("status") == "pending" and (not s.get("tool_name") or s.get("tool_name") == tool_name):
                                matched_step = s
                                break

                        if matched_step:
                            step_id = matched_step["id"]
                            action_label = self._get_action_label(tool_name, params)
                            matched_step.update({"action": action_label, "tool_name": tool_name, "params": params, "status": "running"})
                        else:
                            step_id = str(len(plan_steps))
                            action_label = self._get_action_label(tool_name, params)
                            plan_steps.append({"id": step_id, "action": action_label, "tool_name": tool_name, "params": params, "status": "running"})

                        yield self._sse("plan", {"plan": plan_steps, "thought": agent_thought})
                        yield self._sse("step_start", {"step_id": step_id, "action": action_label, "tool_name": tool_name, "params": params})

                        tool_result = await toolhub.run_tool(tool_name, **params)
                        logger.info(f"{tool_name} 执行结果: {tool_result}")
                        results[tool_name] = tool_result
                        previous_results[tool_name] = tool_result

                        for s in plan_steps:
                            if s["id"] == step_id:
                                s["status"] = "done"

                        thought_summary = self._result_summary(tool_name, tool_result)
                        step_thoughts[step_id] = thought_summary
                        yield self._sse("step_complete", {"step_id": step_id, "result": tool_result, "thought_summary": thought_summary, "tool_name": tool_name, "params": params})

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

                        obs_msg = f"<observation>{json.dumps(tool_result, ensure_ascii=False)}</observation>"
                        messages.append(ChatMessage(role=MessageRole.USER, content=obs_msg))

                    except Exception as e:
                        logger.error(f"执行工具失败: {e}", exc_info=True)
                        error_msg = f"<observation>工具执行错误: {str(e)}</observation>"
                        messages.append(ChatMessage(role=MessageRole.USER, content=error_msg))
                else:
                    logger.warning(f"未找到 action 或 final_answer: {content}")
                    break

            logger.warning(f"达到最大迭代次数 {max_iterations}")
            yield self._sse("error", {"message": "执行超时，请重试"})
            yield self._sse("done", {})

        except Exception as e:
            logger.error(f"ReAct 模式错误: {e}", exc_info=True)
            yield self._sse("error", {"message": str(e)})
            yield self._sse("done", {})

    def _get_action_label(self, tool_name: str, params: dict) -> str:
        """获取工具执行的描述标签"""
        meta = toolhub.get_tool(tool_name)
        if meta:
            return meta.get_action_label(params)
        return tool_name or "执行任务"

    def _result_summary(self, tool_name: str, result: Any) -> str:
        """从工具结果生成简短总结（通用：按常见返回字段推断）"""
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

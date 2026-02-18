import json
import asyncio
import uuid
import random
from datetime import datetime, timezone
from typing import AsyncGenerator, List, Optional, Dict, Any
from app.core.database import get_db
from app.core.config import settings
from app.core.logger import logger
from app.domain.llm_scheduler import MessageRole, llm_service, ChatMessage
from app.tools.toolhub import toolhub
from app.services.document_service import document_service


class SessionService:
    def create_session(self, user_id: str, title: str = "New Chat", mode: str = "normal") -> dict:
        logger.info(f"为用户创建新会话 - 用户: {user_id}, 模式: {mode}, 标题: {title[:30]}...")
        db = get_db()
        session_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        db.execute(
            "INSERT INTO sessions (id, user_id, title, mode, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            (session_id, user_id, title, mode, now, now)
        )
        db.commit()
        logger.debug(f"会话创建成功: {session_id}")
        return {"id": session_id, "user_id": user_id, "title": title, "mode": mode, "created_at": now, "updated_at": now}

    def get_session(self, session_id: str) -> Optional[dict]:
        db = get_db()
        row = db.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
        if row:
            return dict(row)
        return None

    def list_sessions(self, user_id: str) -> List[dict]:
        db = get_db()
        rows = db.execute(
            "SELECT * FROM sessions WHERE user_id = ? ORDER BY updated_at DESC", (user_id,)
        ).fetchall()
        return [dict(r) for r in rows]

    def update_session_title(self, session_id: str, title: str):
        db = get_db()
        now = datetime.now(timezone.utc).isoformat()
        db.execute("UPDATE sessions SET title = ?, updated_at = ? WHERE id = ?", (title, now, session_id))
        db.commit()

    def delete_session(self, session_id: str):
        db = get_db()
        db.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
        db.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        db.commit()

    def add_message(self, session_id: str, role: str, content: str, msg_type: str = "text", metadata: dict = None) -> dict:
        logger.debug(f"添加消息到会话 {session_id}, 角色: {role}, 内容长度: {len(content)}")
        db = get_db()
        msg_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        metadata_json = json.dumps(metadata, ensure_ascii=False) if metadata else None
        db.execute(
            "INSERT INTO messages (id, session_id, role, content, msg_type, metadata_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (msg_id, session_id, role, content, msg_type, metadata_json, now)
        )
        if role == "user":
            count = db.execute("SELECT COUNT(*) FROM messages WHERE session_id = ? AND role = 'user'", (session_id,)).fetchone()[0]
            if count <= 1:
                title = content[:50] + ("..." if len(content) > 50 else "")
                logger.info(f"更新会话标题: {session_id} -> {title[:30]}...")
                db.execute("UPDATE sessions SET title = ?, updated_at = ? WHERE id = ?", (title, now, session_id))
            else:
                db.execute("UPDATE sessions SET updated_at = ? WHERE id = ?", (now, session_id))
        db.commit()
        logger.debug(f"消息添加成功: {msg_id}")
        return {"id": msg_id, "session_id": session_id, "role": role, "content": content, "msg_type": msg_type, "metadata": metadata, "created_at": now}

    def get_messages(self, session_id: str) -> List[dict]:
        db = get_db()
        rows = db.execute(
            "SELECT id, session_id, role, content, msg_type, metadata_json, created_at FROM messages WHERE session_id = ? ORDER BY created_at",
            (session_id,)
        ).fetchall()
        messages = []
        for row in rows:
            msg = dict(row)
            msg["metadata"] = json.loads(msg["metadata_json"]) if msg["metadata_json"] else None
            del msg["metadata_json"]
            messages.append(msg)
        return messages


class AgentService:
    def __init__(self):
        self.session_service = SessionService()

    def _sse(self, event_type: str, data: dict) -> str:
        data["timestamp"] = datetime.now(timezone.utc).isoformat()
        return f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

    async def run_normal_chat(
        self, 
        query: str, 
        session_id: str, 
        history: List[dict], 
        web_search: bool = False
    ) -> AsyncGenerator[str, None]:
        """普通问答模式 - 流式返回直接回答。"""
        print(f"[DEBUG] 收到消息: {query}")
        
        try:
            messages = [
                ChatMessage(role=MessageRole.USER, content=query)
            ]

            full_answer = ""
            async for chunk in llm_service.chat_stream(messages, provider="deepseek"):
                yield self._sse("stream", {"content": chunk})
                full_answer += chunk

            self.session_service.add_message(session_id, "assistant", full_answer)
            yield self._sse("done", {"content": full_answer})
            print(f"[DEBUG] 回复完成: {full_answer[:50]}...")
            
        except Exception as e:
            print(f"[ERROR] {e}")
            error_msg = f"抱歉，发生了错误：{str(e)}"
            yield self._sse("stream", {"content": error_msg})
            self.session_service.add_message(session_id, "assistant", error_msg)
            yield self._sse("done", {"content": error_msg})

    async def run_agent_chat(
        self, 
        query: str, 
        session_id: str, 
        history: List[dict], 
        web_search: bool = False,
        document_ids: Optional[List[str]] = None
    ) -> AsyncGenerator[str, None]:
        """Agent模式 - 智能规划、调用工具、生成回答。"""
        logger.info(f"开始Agent聊天 - 会话: {session_id}, 查询: {query[:50]}...")
        document_ids = document_ids or []

        def serialize(obj):
            if hasattr(obj, 'model_dump'):
                return obj.model_dump()
            if hasattr(obj, 'dict'):
                return obj.dict()
            raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")

        tool_descriptions = []
        for t in toolhub.list_tools():
            desc = f"- {t['name']}: {t['description']}\n"
            if t.get('parameters'):
                param_list = []
                for param_name, param_info in t['parameters'].items():
                    req_str = " (必填)" if param_info.get('required') else ""
                    default_str = f" [默认: {param_info.get('default')}]" if 'default' in param_info else ""
                    param_list.append(f"  - {param_name}: {param_info['description']}{req_str}{default_str}")
                desc += "\n".join(param_list)
            tool_descriptions.append(desc)
        tool_descriptions = "\n\n".join(tool_descriptions)

        doc_context = ""
        if document_ids:
            doc_list = []
            for did in document_ids:
                doc = document_service.get_document(did)
                if doc:
                    doc_list.append(f"  - {did}: {doc.get('original_name', '')} (可编辑)")
            if doc_list:
                doc_context = f"""
        ## 用户选中的可编辑文档（可使用 DocEditTool 进行增删改查）：
        {"".join(doc_list)}
        当用户要求修改、补充、润色或编辑文档时，请使用 DocEditTool，doc_id 从上述列表中选取。
        """

        system_prompt = f"""你是一位智能研究助手 Agent。你的任务是分析用户的查询，自主决定需要哪些步骤，调用合适的工具，并最终生成专业的回答。
        {doc_context}

        ## 可用工具（包含参数说明）：
        {tool_descriptions}

        ## 你的工作流程：
        1. 首先分析用户查询，理解任务意图
        2. 规划执行步骤（可以使用多个工具）
        3. 调用必要的工具获取信息
        4. 整合工具返回的结果
        5. 生成最终的专业回答

        ## 规划步骤时的 JSON 格式：
        请直接输出 JSON 格式的计划，不要包含任何其他文本。必须包含 "thought" 字段，用一两句话说明你的理解和执行思路。
        {{
        "thought": "简要说明你对用户需求的理解和将采取的步骤",
        "plan": [
            {{
            "id": "step_1",
            "action": "执行的动作描述",
            "tool": "要使用的工具名称（如果不需要工具则填 null）",
            "tool_input": {{"param1": "值1"}},
            "status": "pending"
            }}
        ]
        }}

        ## 重要说明：
        - tool_input 必须是一个对象（字典），键是参数名，值是参数值
        - 如果是简单工具（只需要 query），也可以用 {{ "query": "..." }} 的格式
        - 只有在需要时才调用工具，简单问题可以直接回答
        - 工具调用完成后，根据结果生成最终回答
        """

        yield self._sse("step_start", {"step_id": "analyze", "action": "分析用户查询"})

        try:
            logger.debug("使用大模型生成执行计划")
            plan_messages = [
                ChatMessage(role=MessageRole.SYSTEM, content=system_prompt),
                ChatMessage(role=MessageRole.USER, content=f"用户查询：{query}\n\n请输出执行计划的 JSON。")
            ]

            plan_response = await llm_service.chat(plan_messages, provider="deepseek", temperature=0.3)
            plan_text = plan_response.content.strip()
            logger.debug(f"大模型计划响应: {plan_text}")

            plan_data = self._parse_plan(plan_text)
            if not plan_data:
                logger.warning("解析计划失败，使用默认计划")
                plan_data = {
                    "thought": f"好的，我来帮您处理：{query[:50]}...",
                    "plan": [
                        {"id": "s1", "action": "搜索学术数据库", "tool": "SearchTool", "tool_input": {"query": query}, "status": "pending"},
                        {"id": "s2", "action": "生成最终答案", "tool": None, "tool_input": None, "status": "pending"}
                    ]
                }
            if "thought" not in plan_data:
                plan_data["thought"] = f"正在分析您的需求并制定执行计划。"

            logger.info(f"执行计划: {len(plan_data['plan'])} 个步骤")
            yield self._sse("plan", {"plan": plan_data["plan"], "thought": plan_data.get("thought", "")})

            tool_results = {}
            all_papers = []
            step_thoughts = {}
            final_plan_steps = []

            for step in plan_data["plan"]:
                step_id = step["id"]
                action = step["action"]
                tool_name = step.get("tool")
                tool_input = step.get("tool_input", query)

                logger.info(f"执行步骤: {step_id} - {action}")
                yield self._sse("step_start", {"step_id": step_id, "action": action})

                if tool_name and toolhub.get_tool(tool_name):
                    logger.debug(f"调用工具: {tool_name}, 输入: {json.dumps(tool_input, ensure_ascii=False)[:100]}...")
                    for pct in [0.25, 0.5, 0.75, 1.0]:
                        await asyncio.sleep(0.2)
                        yield self._sse("step_progress", {"step_id": step_id, "progress": pct, "message": f"处理中..."})

                    tool_params = {}
                    if isinstance(tool_input, dict):
                        tool_params = tool_input
                    elif isinstance(tool_input, str):
                        tool_params = {"query": tool_input}
                    elif query:
                        tool_params = {"query": query}

                    result = await toolhub.run_tool(tool_name, **tool_params)
                    tool_results[step_id] = result
                    logger.debug(f"工具 {tool_name} 结果: {json.dumps(result, ensure_ascii=False, default=serialize)}")

                    if tool_name == "SearchTool" and result and result.get("papers"):
                        all_papers.extend(result["papers"])
                        logger.info(f"找到 {len(result['papers'])} 篇论文")

                    if tool_name == "DocEditTool" and result and result.get("success") and result.get("action") != "read":
                        doc_id = tool_params.get("doc_id", "")
                        if doc_id:
                            yield self._sse("doc_updated", {"doc_id": doc_id})

                    thought_summary = self._format_step_thought(tool_name, action, result, tool_params)
                    step_thoughts[step_id] = thought_summary
                    final_plan_steps.append({"id": step_id, "action": action, "status": "done", "progress": 1})
                    yield self._sse("step_complete", {"step_id": step_id, "result": result, "thought_summary": thought_summary})
                else:
                    logger.debug(f"步骤 {step_id} 不需要工具")
                    step_thoughts[step_id] = action
                    final_plan_steps.append({"id": step_id, "action": action, "status": "done", "progress": 1})
                    yield self._sse("step_complete", {"step_id": step_id, "result": {"message": "步骤完成"}, "thought_summary": action})

            logger.info("生成最终答案")
            yield self._sse("step_start", {"step_id": "final", "action": "生成最终答案"})

            answer_system_prompt = """你是一位专业的研究助手。请根据用户查询和已获取的工具结果，生成一份全面、专业的最终回答。

            请遵循以下要求：
            1. 使用清晰的结构组织回答
            2. 引用相关论文时使用 [1], [2] 这样的格式
            3. 内容要专业、准确、有条理
            4. 语言简洁明了
            5. 如果有论文信息，请在最后添加参考文献部分

            以下是工具执行结果：
            """

            tool_context = json.dumps(tool_results, ensure_ascii=False, indent=2, default=serialize)
            answer_messages = [
                ChatMessage(role=MessageRole.SYSTEM, content=answer_system_prompt + tool_context),
                ChatMessage(role=MessageRole.USER, content=f"用户查询：{query}\n\n请生成最终回答。")
            ]

            full_summary = ""
            async for chunk in llm_service.chat_stream(answer_messages, provider="deepseek", temperature=0.7):
                yield self._sse("stream", {"content": chunk})
                full_summary += chunk

            logger.info(f"最终答案生成完成，长度: {len(full_summary)}")
            yield self._sse("step_complete", {"step_id": "final", "result": {"answer_length": len(full_summary)}})

            citations = []
            for i, p in enumerate(all_papers[:5]):
                try:
                    authors = "Unknown"
                    if p.get('publicationInfo'):
                        pub_parts = p['publicationInfo'].split(' - ')
                        if pub_parts:
                            authors = pub_parts[0]
                    
                    venue = "Unknown"
                    if p.get('publicationInfo'):
                        pub_parts = p['publicationInfo'].split(' - ')
                        if len(pub_parts) > 2:
                            venue = pub_parts[-1]
                    
                    year = p.get('year', 'Unknown')
                    title = p.get('title', 'Unknown Title')
                    
                    citations.append(f"[{i+1}] {authors} ({year}). {title}. {venue}.")
                except Exception as e:
                    logger.warning(f"生成引用失败: {e}")
                    citations.append(f"[{i+1}] {p.get('title', 'Unknown')}.")
            agent_thought = plan_data.get("thought", "")
            self.session_service.add_message(session_id, "assistant", full_summary, msg_type="text",
                                            metadata={
                                                "mode": "agent",
                                                "papers": all_papers,
                                                "citations": citations,
                                                "tool_results": tool_results,
                                                "task_plan": final_plan_steps,
                                                "agent_thought": agent_thought,
                                                "step_thoughts": step_thoughts,
                                            })
            logger.info(f"Agent聊天完成 - 会话: {session_id}")
            yield self._sse("done", {"content": full_summary})

        except Exception as e:
            logger.error(f"Agent聊天失败: {e}", exc_info=True)
            error_msg = f"抱歉，处理过程中发生了错误：{str(e)}"
            yield self._sse("stream", {"content": error_msg})
            self.session_service.add_message(session_id, "assistant", error_msg)
            yield self._sse("done", {"content": error_msg})

    def _format_step_thought(self, tool_name: str, action: str, result: dict, tool_params: dict) -> str:
        """生成步骤的简要思考描述"""
        if not result:
            return action
        if tool_name == "SearchTool":
            n = len(result.get("papers", []))
            return f"检索学术论文 · 找到 {n} 篇相关文献" if n > 0 else "检索学术论文 · 未找到相关文献"
        if tool_name == "DocEditTool":
            act = result.get("action", "")
            fn = ""
            if act == "read":
                fn = result.get("filename", tool_params.get("doc_id", ""))[:20]
                return f"读取文档 · {fn}"
            if result.get("success"):
                return f"编辑文档 · {result.get('message', act)}"
            return f"编辑文档 · {result.get('error', '失败')}"
        if tool_name == "DocTool":
            return f"文档管理 · {result.get('result', action)}"
        if tool_name == "SummarizeTool":
            return "生成摘要 · 完成"
        if tool_name == "FilterTool":
            return "筛选论文 · 完成"
        if tool_name == "CitationTool":
            return "生成引用 · 完成"
        if tool_name == "ProfileTool":
            return "查询用户画像 · 完成"
        if tool_name == "MultiModalRAGTool":
            return "文档检索问答 · 完成"
        return action

    def _parse_plan(self, text: str) -> Optional[Dict[str, Any]]:
        """解析 LLM 返回的计划 JSON"""
        try:
            text = text.strip()
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            return json.loads(text.strip())
        except Exception as e:
            logger.warning(f"解析计划失败: {e}")
            return None

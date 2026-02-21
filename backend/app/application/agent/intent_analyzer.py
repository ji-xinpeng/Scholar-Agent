import json
from typing import Dict, Any, Optional, NamedTuple
from enum import Enum
from app.infrastructure.logging.config import logger
from app.infrastructure.llm.service import MessageRole, ChatMessage, llm_service


class ChatIntent(Enum):
    """对话意图类型（路由用）"""
    SIMPLE = "simple"  # 简单对话
    PAPER_QA = "paper_qa"  # 论文问答
    AGENT = "agent"  # 复杂任务（智能体模式）


class TaskType:
    """细粒度任务类型（用于匹配不同 prompt，与 intent_prompts 中 key 一致）"""
    SIMPLE_CHAT = "simple_chat"           # 简单聊聊
    FILTER_LITERATURE = "filter_literature"   # 筛选文献
    UNDERSTAND_PAPER = "understand_paper"     # 理解与解读论文
    RESEARCH_IDEAS = "research_ideas"          # 梳理研究思路
    WRITE_PAPER = "write_paper"                # 撰写与润色论文
    PLAN_RESEARCH = "plan_research"            # 规划研究步骤与时间线
    GENERAL = "general"                         # 未细分或综合


class IntentResult(NamedTuple):
    """意图分析结果：路由意图 + 细粒度任务类型"""
    intent: ChatIntent
    task_type: str  # TaskType.xxx


class IntentAnalyzer:
    """
    意图识别器 - 准确分析用户查询意图
    
    识别优先级：
    1. 先做快速规则判断（提高响应速度）
    2. 规则判断有疑问时，用 LLM 分析
    3. 最后结合所有信息做决策
    """

    def __init__(self):
        self._system_prompt = """你是智能学术助手「小研」背后的意图识别模块，需要同时判断两件事：

一、路由意图 (intent)，三选一：
1. simple - 简单对话：问候/闲聊/感谢/询问你能做什么、直接的知识问答、不需要文档或工具即可回答的短问题。
2. paper_qa - 论文问答：问题明确针对用户已选中文档的内容（总结、解释、摘取等），且当前有选中文档。
3. agent - 复杂任务：需要搜索/下载/多步骤规划/联网查最新信息/查找或筛选文献/分析比较总结等，适合用工具链完成。

二、任务类型 (task_type)，用于优化回答风格，七选一：
- simple_chat: 简单聊聊（问候、闲聊、问能力等）
- filter_literature: 筛选文献（找文献、推荐、按条件筛选、检索）
- understand_paper: 理解与解读论文（解释某篇/某类论文、概念、方法、结论）
- research_ideas: 梳理研究思路（选题、方向、思路、论证逻辑）
- write_paper: 撰写与润色论文（写提纲、某章节、摘要、润色、改表述）
- plan_research: 规划研究步骤与时间线（步骤拆解、时间安排、里程碑）
- general: 其他或综合（知识问答、无法归入以上某一类）

重要提示：
- 有选中文档且问题明确关于文档内容时选 paper_qa，否则按问题性质选 simple 或 agent。
- task_type 与 intent 可独立：例如 intent=agent 时 task_type 可能是 filter_literature 或 plan_research。

请严格按以下 JSON 输出，不要多余文字：
{"intent": "simple|paper_qa|agent", "task_type": "simple_chat|filter_literature|understand_paper|research_ideas|write_paper|plan_research|general", "reason": "简短理由"}"""

    async def analyze(
        self,
        query: str,
        has_selected_docs: bool = False
    ) -> IntentResult:
        """分析用户查询意图与细粒度任务类型
        
        Args:
            query: 用户查询
            has_selected_docs: 是否有选中的文档
            
        Returns:
            IntentResult(intent=路由意图, task_type=任务类型)
        """
        try:
            logger.info(f"开始意图识别 - 查询: '{query}', 有选中文档: {has_selected_docs}")

            # 1. 明显是 simple 的情况（问候、感谢、问能力等 -> simple_chat）
            simple_intent = self._check_simple_intent(query)
            if simple_intent:
                task_type = TaskType.SIMPLE_CHAT if self._is_greeting_or_system_query(query) else TaskType.GENERAL
                logger.info(f"快速判断为 simple, task_type={task_type}: {query}")
                return IntentResult(ChatIntent.SIMPLE, task_type)

            # 2. 明显是 agent 的情况（规则只能判断路由，任务类型交给 LLM 或用 general）
            agent_intent = self._check_agent_intent(query)
            if agent_intent:
                logger.info(f"快速判断为 agent，使用 LLM 细化 task_type: {query}")
                return await self._analyze_with_llm(query, has_selected_docs)

            # 3. 有选中文档且问题明确关于文档
            if has_selected_docs:
                paper_qa_intent = self._check_paper_qa_intent(query)
                if paper_qa_intent:
                    logger.info(f"判断为 paper_qa: {query}")
                    return IntentResult(ChatIntent.PAPER_QA, TaskType.UNDERSTAND_PAPER)

            # 4. 规则不确定时，用 LLM 同时得到 intent 和 task_type
            logger.info(f"规则判断不确定，使用 LLM 分析: {query}")
            return await self._analyze_with_llm(query, has_selected_docs)

        except Exception as e:
            logger.error(f"意图识别错误: {e}", exc_info=True)
            return IntentResult(ChatIntent.SIMPLE, TaskType.GENERAL)

    def _check_simple_intent(self, query: str) -> bool:
        """检查是否是简单对话"""
        query_lower = query.lower().strip()

        # 问候类
        greeting_keywords = ["你好", "hi", "hello", "嗨", "早上好", "下午好", "晚上好", "hey"]
        for kw in greeting_keywords:
            if kw in query_lower:
                return True

        # 感谢/道别类
        thanks_keywords = ["谢谢", "感谢", "thank", "thanks", "再见", "bye", "拜拜", "goodbye"]
        for kw in thanks_keywords:
            if kw in query_lower:
                return True

        # 简单确认类
        confirm_keywords = ["好的", "嗯", "哦", "对", "是的", "没错", "ok", "okay"]
        if len(query_lower) <= 10 and any(kw in query_lower for kw in confirm_keywords):
            return True

        # 询问系统信息
        system_questions = [
            "你是谁", "你叫什么", "你能做什么", "你有什么功能",
            "介绍一下自己", "你是谁啊", "你是", "你是做什么的",
            "what are you", "who are you", "what can you do"
        ]
        for q in system_questions:
            if q in query_lower:
                return True

        # 非常短且没有特殊关键词的问题
        short_question_keywords = ["搜索", "查找", "下载", "论文", "研究", "分析", "比较", "总结", "最新", "最近", "文档"]
        if len(query) < 25 and not any(kw in query_lower for kw in short_question_keywords):
            return True

        return False

    def _is_greeting_or_system_query(self, query: str) -> bool:
        """是否属于问候或询问系统能力（用于给 task_type=simple_chat）"""
        q = query.lower().strip()
        greeting = ["你好", "hi", "hello", "嗨", "早上好", "下午好", "晚上好", "hey", "谢谢", "感谢", "再见", "bye", "拜拜"]
        system_q = ["你是谁", "你叫什么", "你能做什么", "你有什么功能", "介绍一下自己", "你是做什么的", "what are you", "who are you", "what can you do"]
        return any(kw in q for kw in greeting + system_q)

    def _check_agent_intent(self, query: str) -> bool:
        """检查是否是复杂任务（需要智能体）"""
        query_lower = query.lower().strip()

        # 需要搜索的关键词
        search_keywords = ["搜索", "查找", "找一下", "帮我找", "搜索一下", "搜索", "search", "find", "look for"]
        
        # 需要下载的关键词
        download_keywords = ["下载", "帮我下载", "下载一下", "download"]
        
        # 需要论文相关操作的关键词
        paper_keywords = ["论文", "文献", "paper", "papers"]
        
        # 复杂分析类关键词
        analysis_keywords = ["分析", "比较", "对比", "总结", "研究", "调研", "整理", "汇总"]
        
        # 最新信息类关键词
        latest_keywords = ["最新", "最近", "新闻", "消息", "趋势", "动态", "now", "latest", "recent"]

        all_keywords = search_keywords + download_keywords + paper_keywords + analysis_keywords + latest_keywords

        if any(kw in query_lower for kw in all_keywords):
            return True

        return False

    def _check_paper_qa_intent(self, query: str) -> bool:
        """检查是否是关于文档的问题"""
        query_lower = query.lower().strip()

        # 明确提到文档的关键词
        document_keywords = [
            "这篇文档", "这个文档", "文档中", "文档里", "关于文档",
            "这篇论文", "这个论文", "论文中", "论文里",
            "选中的文档", "选中的论文",
            "文档内容", "论文内容",
            "总结文档", "总结论文", "分析文档", "分析论文"
        ]

        if any(kw in query_lower for kw in document_keywords):
            return True

        return False

    async def _analyze_with_llm(
        self,
        query: str,
        has_selected_docs: bool = False
    ) -> IntentResult:
        """使用 LLM 进行意图与任务类型识别"""
        try:
            user_prompt = f"用户查询: {query}\n\n"
            if has_selected_docs:
                user_prompt += "用户已选中文档（注意：只有当问题明确是关于文档内容时才选 paper_qa）\n"

            messages = [
                ChatMessage(role=MessageRole.SYSTEM, content=self._system_prompt),
                ChatMessage(role=MessageRole.USER, content=user_prompt)
            ]

            response = await llm_service.chat(messages)
            content = response.content or ""

            valid_task_types = {
                "simple_chat", "filter_literature", "understand_paper",
                "research_ideas", "write_paper", "plan_research", "general"
            }

            try:
                json_start = content.find("{")
                json_end = content.rfind("}")
                if json_start >= 0 and json_end > json_start:
                    json_str = content[json_start:json_end+1]
                    result = json.loads(json_str)
                    intent_str = result.get("intent", "simple")
                    task_type = (result.get("task_type") or "general").strip().lower()
                    if task_type not in valid_task_types:
                        task_type = "general"
                    logger.info(f"LLM意图识别: intent={intent_str}, task_type={task_type}, 理由: {result.get('reason')}")

                    intent_map = {
                        "simple": ChatIntent.SIMPLE,
                        "paper_qa": ChatIntent.PAPER_QA,
                        "agent": ChatIntent.AGENT
                    }
                    return IntentResult(intent_map.get(intent_str, ChatIntent.SIMPLE), task_type)
            except (json.JSONDecodeError, ValueError):
                pass

            # 解析失败时回退
            if "simple" in content.lower():
                return IntentResult(ChatIntent.SIMPLE, TaskType.GENERAL)
            if "paper_qa" in content.lower() or "paper qa" in content.lower():
                return IntentResult(ChatIntent.PAPER_QA, TaskType.UNDERSTAND_PAPER)
            return IntentResult(ChatIntent.AGENT, TaskType.GENERAL)

        except Exception as e:
            logger.error(f"LLM意图识别错误: {e}", exc_info=True)
            return IntentResult(ChatIntent.SIMPLE, TaskType.GENERAL)


intent_analyzer = IntentAnalyzer()

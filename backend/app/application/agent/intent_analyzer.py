import json
from typing import Dict, Any, Optional
from enum import Enum
from app.infrastructure.logging.config import logger
from app.infrastructure.llm.service import MessageRole, ChatMessage, llm_service


class ChatIntent(Enum):
    """对话意图类型"""
    SIMPLE = "simple"  # 简单对话
    PAPER_QA = "paper_qa"  # 论文问答
    AGENT = "agent"  # 复杂任务（智能体模式）


class IntentAnalyzer:
    """
    意图识别器 - 准确分析用户查询意图
    
    识别优先级：
    1. 先做快速规则判断（提高响应速度）
    2. 规则判断有疑问时，用 LLM 分析
    3. 最后结合所有信息做决策
    """

    def __init__(self):
        self._system_prompt = """你是一个专业的意图识别助手，需要准确分析用户查询的意图。

请根据用户查询内容，判断以下三种意图之一：

1. simple - 简单对话
- 简单的问候、闲聊（你好、hi、谢谢、再见等）
- 直接的知识问答，不需要复杂工具
- 简短的问题，上下文明确
- 询问系统信息（你是谁、你能做什么等）
- 不需要任何文档或工具就能回答的问题

2. paper_qa - 论文问答
- 问题明确涉及用户已选中文档的内容
- 用户明确要求基于某个文档回答
- 问题明显是关于已有文档的查询、总结、分析

3. agent - 复杂任务
- 需要多步骤规划和执行
- 需要搜索、下载等工具
- 问题复杂，需要分解执行
- 需要联网搜索最新信息
- 需要查找、下载论文或资料
- 需要进行数据分析、比较、总结等

重要提示：
- 即使有选中的文档，如果问题明显不是关于文档的，也不应该选择 paper_qa
- 如果是问候、闲聊或询问系统信息，即使有文档也应该选择 simple
- 只有当问题明确是关于文档内容时，才选择 paper_qa

请用JSON格式输出，格式：{"intent": "simple|paper_qa|agent", "reason": "简短理由"}"""

    async def analyze(
        self,
        query: str,
        has_selected_docs: bool = False
    ) -> ChatIntent:
        """分析用户查询意图
        
        Args:
            query: 用户查询
            has_selected_docs: 是否有选中的文档
            
        Returns:
            意图类型
        """
        try:
            logger.info(f"开始意图识别 - 查询: '{query}', 有选中文档: {has_selected_docs}")

            # 1. 首先检查明显是 simple 的情况
            simple_intent = self._check_simple_intent(query)
            if simple_intent:
                logger.info(f"快速判断为 simple: {query}")
                return ChatIntent.SIMPLE

            # 2. 检查明显是 agent 的情况
            agent_intent = self._check_agent_intent(query)
            if agent_intent:
                logger.info(f"快速判断为 agent: {query}")
                return ChatIntent.AGENT

            # 3. 如果有选中文档，检查是否是关于文档的问题
            if has_selected_docs:
                paper_qa_intent = self._check_paper_qa_intent(query)
                if paper_qa_intent:
                    logger.info(f"判断为 paper_qa: {query}")
                    return ChatIntent.PAPER_QA

            # 4. 规则判断不确定时，用 LLM 分析
            logger.info(f"规则判断不确定，使用 LLM 分析: {query}")
            return await self._analyze_with_llm(query, has_selected_docs)

        except Exception as e:
            logger.error(f"意图识别错误: {e}", exc_info=True)
            return ChatIntent.SIMPLE  # 出错时默认返回 simple 更安全

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
    ) -> ChatIntent:
        """使用LLM进行意图识别"""
        try:
            user_prompt = f"用户查询: {query}\n\n"
            if has_selected_docs:
                user_prompt += "用户已选中文档（注意：只有当问题明确是关于文档内容时才选择 paper_qa）\n"

            messages = [
                ChatMessage(role=MessageRole.SYSTEM, content=self._system_prompt),
                ChatMessage(role=MessageRole.USER, content=user_prompt)
            ]

            response = await llm_service.chat(messages)
            content = response.content or ""

            # 尝试解析JSON
            try:
                json_start = content.find("{")
                json_end = content.rfind("}")
                if json_start >= 0 and json_end > json_start:
                    json_str = content[json_start:json_end+1]
                    result = json.loads(json_str)
                    intent_str = result.get("intent", "simple")
                    logger.info(f"LLM意图识别: {intent_str}, 理由: {result.get('reason')}")
                    
                    intent_map = {
                        "simple": ChatIntent.SIMPLE,
                        "paper_qa": ChatIntent.PAPER_QA,
                        "agent": ChatIntent.AGENT
                    }
                    return intent_map.get(intent_str, ChatIntent.SIMPLE)
            except (json.JSONDecodeError, ValueError):
                pass

            # 如果解析失败，根据内容判断
            if "simple" in content.lower():
                return ChatIntent.SIMPLE
            elif "paper" in content.lower() or "qa" in content.lower():
                return ChatIntent.PAPER_QA
            else:
                return ChatIntent.SIMPLE

        except Exception as e:
            logger.error(f"LLM意图识别错误: {e}", exc_info=True)
            return ChatIntent.SIMPLE


intent_analyzer = IntentAnalyzer()

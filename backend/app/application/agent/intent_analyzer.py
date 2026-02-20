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
    """意图识别器 - 自动识别用户查询意图"""

    def __init__(self):
        self._system_prompt = """你是一个意图识别助手，需要分析用户查询的意图。

        请根据用户查询内容，判断以下三种意图之一：

        1. simple - 简单对话
        - 简单的问候、闲聊
        - 直接的知识问答，不需要复杂工具
        - 简短的问题，上下文明确

        2. paper_qa - 论文问答
        - 问题涉及文档或论文内容
        - 用户有选中的文档
        - 问题明显是关于已有文档的

        3. agent - 复杂任务
        - 需要多步骤规划
        - 需要搜索、下载等工具
        - 问题复杂，需要分解执行
        - 需要联网搜索最新信息

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
            # 快速规则判断
            if has_selected_docs:
                # 如果有选中的文档，优先考虑论文问答
                logger.info(f"有选中文档，优先paper_qa模式")
                return ChatIntent.PAPER_QA

            # 简单关键词规则
            simple_keywords = ["你好", "hi", "hello", "谢谢", "再见", "bye", "好的", "嗯", "哦"]
            for kw in simple_keywords:
                if kw in query.lower():
                    return ChatIntent.SIMPLE

            # 长度较短的简单问题
            if len(query) < 30 and not any(kw in query for kw in ["搜索", "查找", "下载", "论文", "研究", "分析", "比较", "总结"]):
                return ChatIntent.SIMPLE

            # 需要智能体的关键词
            agent_keywords = ["搜索", "查找", "下载", "论文", "研究", "分析", "比较", "总结", "最新", "最近", "新闻", "趋势"]
            if any(kw in query for kw in agent_keywords):
                return ChatIntent.AGENT

            # 如果规则无法判断，用LLM分析
            return await self._analyze_with_llm(query, has_selected_docs)

        except Exception as e:
            logger.error(f"意图识别错误: {e}", exc_info=True)
            # 默认返回智能体模式，以确保功能完整性
            return ChatIntent.AGENT

    async def _analyze_with_llm(
        self,
        query: str,
        has_selected_docs: bool = False
    ) -> ChatIntent:
        """使用LLM进行意图识别"""
        try:
            user_prompt = f"用户查询: {query}\n\n"
            if has_selected_docs:
                user_prompt += "用户已选中文档\n"

            messages = [
                ChatMessage(role=MessageRole.SYSTEM, content=self._system_prompt),
                ChatMessage(role=MessageRole.USER, content=user_prompt)
            ]

            response = await llm_service.chat(messages)
            content = response.content or ""

            # 尝试解析JSON
            try:
                # 提取JSON部分
                json_start = content.find("{")
                json_end = content.rfind("}")
                if json_start >= 0 and json_end > json_start:
                    json_str = content[json_start:json_end+1]
                    result = json.loads(json_str)
                    intent_str = result.get("intent", "agent")
                    logger.info(f"LLM意图识别: {intent_str}, 理由: {result.get('reason')}")
                    
                    intent_map = {
                        "simple": ChatIntent.SIMPLE,
                        "paper_qa": ChatIntent.PAPER_QA,
                        "agent": ChatIntent.AGENT
                    }
                    return intent_map.get(intent_str, ChatIntent.AGENT)
            except (json.JSONDecodeError, ValueError):
                pass

            # 如果解析失败，根据内容判断
            if "simple" in content.lower():
                return ChatIntent.SIMPLE
            elif "paper" in content.lower() or "qa" in content.lower():
                return ChatIntent.PAPER_QA
            else:
                return ChatIntent.AGENT

        except Exception as e:
            logger.error(f"LLM意图识别错误: {e}", exc_info=True)
            return ChatIntent.AGENT


intent_analyzer = IntentAnalyzer()

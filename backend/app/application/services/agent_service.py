from typing import AsyncGenerator, List, Optional
from app.application.agent.orchestrator import agent_orchestrator
from app.application.services.session_service import SessionService
from app.infrastructure.logging.config import logger


class AgentService:
    """Agent 服务层 - ReAct 模式"""
    
    def __init__(self):
        self.session_service = SessionService()

    async def run_normal_chat(
        self, 
        query: str, 
        session_id: str, 
        history: List[dict] = None, 
        web_search: bool = False,
        document_ids: Optional[List[str]] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """普通问答模式 - 流式返回直接回答"""
        logger.info(f"普通聊天模式调用")
        async for chunk in agent_orchestrator.run_normal_chat(
            session_id, "default", query, document_ids, None, web_search,
            provider=provider, model=model
        ):
            yield chunk

    async def run_agent_chat(
        self, 
        query: str, 
        session_id: str, 
        history: List[dict] = None, 
        web_search: bool = False,
        document_ids: Optional[List[str]] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """智能体模式 - ReAct 模式（思考-行动-观察循环）"""
        logger.info(f"智能体模式调用 (ReAct)")
        async for chunk in agent_orchestrator.run_agent_chat(
            session_id, "default", query, document_ids,
            llm_provider=provider, llm_model=model
        ):
            yield chunk

    async def run_paper_qa_chat(
        self, 
        query: str, 
        session_id: str, 
        history: List[dict] = None, 
        document_ids: Optional[List[str]] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """论文问答模式 - 仅基于已有文档进行问答"""
        logger.info(f"论文问答模式调用")
        async for chunk in agent_orchestrator.run_paper_qa_chat(
            session_id, "default", query, document_ids,
            llm_provider=provider, llm_model=model
        ):
            yield chunk


agent_service = AgentService()

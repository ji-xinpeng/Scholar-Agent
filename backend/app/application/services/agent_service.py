from typing import AsyncGenerator, List, Optional
from app.application.agent.orchestrator import agent_orchestrator
from app.application.services.session_service import SessionService
from app.infrastructure.logging.config import logger


class AgentService:
    """Agent 服务层 - 向后兼容的服务类"""
    
    def __init__(self):
        self.session_service = SessionService()

    async def run_normal_chat(
        self, 
        query: str, 
        session_id: str, 
        history: List[dict] = None, 
        web_search: bool = False,
        document_ids: Optional[List[str]] = None
    ) -> AsyncGenerator[str, None]:
        """普通问答模式 - 流式返回直接回答（向后兼容）"""
        logger.info(f"向后兼容的普通聊天模式调用")
        async for chunk in agent_orchestrator.run_normal_chat(
            session_id, "default", query, document_ids, None, web_search
        ):
            yield chunk

    async def run_agent_chat(
        self, 
        query: str, 
        session_id: str, 
        history: List[dict] = None, 
        web_search: bool = False,
        document_ids: Optional[List[str]] = None
    ) -> AsyncGenerator[str, None]:
        """Agent模式 - 智能规划、调用工具、生成回答（向后兼容）"""
        logger.info(f"向后兼容的 Agent 聊天模式调用")
        async for chunk in agent_orchestrator.run_scholar_chat(
            session_id, "default", query, document_ids
        ):
            yield chunk


agent_service = AgentService()

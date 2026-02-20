from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from app.schemas import ChatRequest, SessionCreate
from app.application.services.agent_service import AgentService
from app.application.agent.orchestrator import agent_orchestrator
from app.core.config import settings
from app.infrastructure.logging.config import logger
import json

router = APIRouter()
agent_service = AgentService()


@router.post("/chat")
async def chat(request: ChatRequest):
    """主聊天接口 - 智能统一入口，自动识别意图并路由，根据意图选择模型"""
    logger.info(f"收到聊天请求 - 用户: {request.user_id}, 深度研究: {request.deep_research}, 会话: {request.session_id or '新会话'}")
    logger.debug(f"消息: {request.message[:100]}...")

    if not request.session_id:
        session = agent_service.session_service.create_session(request.user_id, mode="agent")
        session_id = session["id"]
        logger.info(f"创建新会话: {session_id}")
    else:
        session_id = request.session_id
        existing = agent_service.session_service.get_session(session_id)
        if not existing:
            session = agent_service.session_service.create_session(request.user_id, mode="agent")
            session_id = session["id"]
            logger.warning(f"会话 {request.session_id} 不存在，创建新会话: {session_id}")
        else:
            logger.debug(f"使用现有会话: {session_id}")

    history = agent_service.session_service.get_messages(session_id)
    logger.debug(f"加载 {len(history)} 条历史消息")

    async def wrapped_generator():
        try:
            if request.deep_research:
                logger.info("深度研究模式：直接使用智能体，使用配置的智能体模型")
                model = request.model or settings.AGENT_MODEL
                async for chunk in agent_orchestrator.run_agent_chat(
                    session_id,
                    request.user_id,
                    request.message,
                    selected_doc_ids=request.document_ids,
                    llm_model=model
                ):
                    yield chunk
            else:
                logger.info("智能模式：由 orchestrator 统一处理，自动选择模型")
                async for chunk in agent_orchestrator.run_unified_chat(
                    session_id,
                    request.user_id,
                    request.message,
                    selected_doc_ids=request.document_ids,
                    llm_model=request.model
                ):
                    yield chunk
            
            logger.info("聊天生成成功完成")
        except Exception as e:
            logger.error(f"聊天生成失败: {e}", exc_info=True)
            raise

    return StreamingResponse(wrapped_generator(), media_type="text/event-stream", headers={
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
        "X-Session-Id": session_id,
    })


@router.get("/sessions")
async def list_sessions(user_id: str = "default"):
    logger.debug(f"列出用户会话 - 用户: {user_id}")
    sessions = agent_service.session_service.list_sessions(user_id)
    logger.info(f"找到用户 {user_id} 的 {len(sessions)} 个会话")
    return {"sessions": sessions, "total": len(sessions)}


@router.post("/sessions")
async def create_session(request: SessionCreate):
    logger.info(f"创建会话 - 用户: {request.user_id}, 标题: {request.title[:30] if request.title else '新聊天'}, 模式: {request.mode}")
    session = agent_service.session_service.create_session(request.user_id, request.title, request.mode)
    logger.debug(f"会话创建成功: {session['id']}")
    return session


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    logger.warning(f"删除会话: {session_id}")
    agent_service.session_service.delete_session(session_id)
    logger.info(f"会话 {session_id} 删除成功")
    return {"status": "ok"}


@router.get("/sessions/{session_id}/messages")
async def get_messages(session_id: str):
    logger.debug(f"获取会话消息 - 会话: {session_id}")
    messages = agent_service.session_service.get_messages(session_id)
    logger.info(f"找到会话 {session_id} 的 {len(messages)} 条消息")
    return {"messages": messages}

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from app.schemas import ChatRequest, SessionCreate
from app.application.services.agent_service import AgentService
from app.application.services.document_service import document_service
from app.infrastructure.logging.config import logger
import json
from datetime import datetime, timezone

router = APIRouter()
agent_service = AgentService()


@router.post("/chat")
async def chat(request: ChatRequest):
    """主聊天接口 - 返回SSE流"""
    logger.info(f"收到聊天请求 - 用户: {request.user_id}, 模式: {request.mode}, 会话: {request.session_id or '新会话'}")
    logger.debug(f"消息: {request.message[:100]}...")

    document_context = ""
    if request.document_ids:
        for doc_id in request.document_ids:
            doc = document_service.get_document(doc_id)
            if doc:
                content = document_service.get_document_content(doc_id)
                if content:
                    document_context += f"\n\n=== 文档: {doc['original_name']} ===\n{content}"
                    logger.info(f"已加载文档: {doc['original_name']}, 长度: {len(content)}")

    enhanced_message = request.message
    if document_context:
        enhanced_message = f"{request.message}\n\n【相关文档内容】{document_context}"

    if not request.session_id:
        session = agent_service.session_service.create_session(request.user_id, mode=request.mode)
        session_id = session["id"]
        logger.info(f"创建新会话: {session_id}")
    else:
        session_id = request.session_id
        existing = agent_service.session_service.get_session(session_id)
        if not existing:
            session = agent_service.session_service.create_session(request.user_id, mode=request.mode)
            session_id = session["id"]
            logger.warning(f"会话 {request.session_id} 不存在，创建新会话: {session_id}")
        else:
            logger.debug(f"使用现有会话: {session_id}")

    history = agent_service.session_service.get_messages(session_id)
    logger.debug(f"加载 {len(history)} 条历史消息")

    async def wrapped_generator():
        try:
            if request.mode == "agent":
                logger.info("启动Agent模式聊天")
                async for chunk in agent_service.run_agent_chat(
                    enhanced_message, session_id, history,
                    web_search=request.web_search,
                    document_ids=request.document_ids
                ):
                    yield chunk
            else:
                logger.info("启动普通模式聊天")
                async for chunk in agent_service.run_normal_chat(enhanced_message, session_id, history, web_search=request.web_search, document_ids=request.document_ids):
                    yield chunk
            logger.info("聊天生成成功完成")
        except Exception as e:
            logger.error(f"聊天生成失败: {e}", exc_info=True)
            raise

    return StreamingResponse(wrapped_generator(), media_type="text/event-stream", headers={
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",  # 禁止代理缓冲，确保 SSE 事件及时推送到前端
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

from fastapi import APIRouter
from app.api.v1.chat.routers import router as chat_router
from app.api.v1.documents.routers import router as documents_router
from app.api.v1.users.routers import router as users_router

api_router = APIRouter()

api_router.include_router(chat_router, prefix="/chat", tags=["chat"])
api_router.include_router(documents_router, prefix="/documents", tags=["documents"])
api_router.include_router(users_router, prefix="/users", tags=["users"])

from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime


# ========== 会话 ==========
class SessionCreate(BaseModel):
    user_id: str = "default"
    title: str = "New Chat"
    mode: str = "normal"


class SessionResponse(BaseModel):
    id: str
    user_id: str
    title: str
    mode: str
    created_at: str
    updated_at: str


class SessionListResponse(BaseModel):
    sessions: List[SessionResponse]
    total: int


# ========== 消息 ==========
class MessageResponse(BaseModel):
    id: str
    session_id: str
    role: str
    content: str
    msg_type: str = "text"
    metadata: Optional[dict] = None
    created_at: str


class MessageListResponse(BaseModel):
    messages: List[MessageResponse]


# ========== 聊天 ==========
class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    user_id: str = "default"
    deep_research: bool = False  # 深度研究模式：允许长时间多步骤规划和大规模搜索
    document_ids: Optional[List[str]] = None
    """当前轮次用户上传的图片，data URL（data:image/xxx;base64,...）用于视觉问答"""
    image_data: Optional[str] = None
    provider: Optional[str] = None  # LLM 提供商，如 "qwen", "deepseek"
    model: Optional[str] = None  # 模型名称，如 "qwen-turbo", "deepseek-chat"


# ========== 文档 ==========
class DocumentResponse(BaseModel):
    id: str
    user_id: str
    folder_id: Optional[str]
    filename: str
    original_name: str
    file_size: int
    file_type: str
    page_count: int
    status: str
    created_at: str


class DocumentListResponse(BaseModel):
    documents: List[DocumentResponse]
    total: int
    page: int
    page_size: int


# ========== 文件夹 ==========
class FolderCreate(BaseModel):
    user_id: str = "default"
    name: str
    parent_id: Optional[str] = None


class FolderResponse(BaseModel):
    id: str
    user_id: str
    name: str
    parent_id: Optional[str]
    created_at: str
    document_count: int = 0


class FolderListResponse(BaseModel):
    folders: List[FolderResponse]


# ========== 用户资料 ==========
class UserProfile(BaseModel):
    model_config = {"protected_namespaces": ()}
    user_id: str
    display_name: str = ""
    avatar_url: str = ""
    research_field: str = ""
    knowledge_level: str = "intermediate"
    institution: str = ""
    bio: str = ""
    model_mode: str = "free"
    balance: float = 0.0
    created_at: str = ""
    updated_at: str = ""


class UserProfileUpdate(BaseModel):
    model_config = {"protected_namespaces": ()}
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    research_field: Optional[str] = None
    knowledge_level: Optional[str] = None
    institution: Optional[str] = None
    bio: Optional[str] = None
    model_mode: Optional[str] = None


# ========== 登录 ==========
class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    password: str
    confirm_password: str


class AuthResponse(BaseModel):
    user_id: str
    username: str


# ========== SSE事件 ==========
class SSEEvent(BaseModel):
    type: str
    data: Any

import hashlib
import uuid
from datetime import datetime, timezone
from app.infrastructure.storage.database.connection import get_db

# 简单盐值，生产环境建议用环境变量
PASSWORD_SALT = "scholar_agent_auth_v1"


def _hash_password(password: str, username: str) -> str:
    raw = f"{PASSWORD_SALT}:{username}:{password}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class AuthService:
    def register(self, username: str, password: str, confirm_password: str) -> dict:
        username = (username or "").strip()
        if not username:
            raise ValueError("用户名不能为空")
        if not password:
            raise ValueError("密码不能为空")
        if password != confirm_password:
            raise ValueError("两次输入的密码不一致")

        db = get_db()
        existing = db.execute("SELECT 1 FROM auth_users WHERE username = ?", (username,)).fetchone()
        if existing:
            raise ValueError("用户名已存在")

        now = datetime.now(timezone.utc).isoformat()
        password_hash = _hash_password(password, username)
        db.execute(
            "INSERT INTO auth_users (username, password_hash, created_at) VALUES (?, ?, ?)",
            (username, password_hash, now),
        )
        db.commit()
        # 使用 username 作为 user_id，并确保 user_profiles 有记录
        from app.application.services.user_service import user_service
        user_service.get_profile(username)
        return {"user_id": username, "username": username}

    def login(self, username: str, password: str) -> dict:
        username = (username or "").strip()
        if not username:
            raise ValueError("用户名不能为空")
        if not password:
            raise ValueError("密码不能为空")

        db = get_db()
        row = db.execute(
            "SELECT username, password_hash FROM auth_users WHERE username = ?",
            (username,),
        ).fetchone()
        if not row:
            raise ValueError("用户名或密码错误")

        password_hash = _hash_password(password, username)
        if row["password_hash"] != password_hash:
            raise ValueError("用户名或密码错误")

        # 确保有 user_profile（首次登录时创建）
        from app.application.services.user_service import user_service
        user_service.get_profile(username)
        return {"user_id": username, "username": username}


auth_service = AuthService()

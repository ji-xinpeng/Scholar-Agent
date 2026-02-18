import json
import uuid
from datetime import datetime, timezone
from typing import List, Optional
from app.infrastructure.storage.database.connection import get_db
from app.infrastructure.logging.config import logger


class SessionService:
    def create_session(self, user_id: str, title: str = "New Chat", mode: str = "normal") -> dict:
        logger.info(f"为用户创建新会话 - 用户: {user_id}, 模式: {mode}, 标题: {title[:30]}...")
        db = get_db()
        session_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        db.execute(
            "INSERT INTO sessions (id, user_id, title, mode, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            (session_id, user_id, title, mode, now, now)
        )
        db.commit()
        logger.debug(f"会话创建成功: {session_id}")
        return {"id": session_id, "user_id": user_id, "title": title, "mode": mode, "created_at": now, "updated_at": now}

    def get_session(self, session_id: str) -> Optional[dict]:
        db = get_db()
        row = db.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
        if row:
            return dict(row)
        return None

    def list_sessions(self, user_id: str) -> List[dict]:
        db = get_db()
        rows = db.execute(
            "SELECT * FROM sessions WHERE user_id = ? ORDER BY updated_at DESC", (user_id,)
        ).fetchall()
        return [dict(r) for r in rows]

    def update_session_title(self, session_id: str, title: str):
        db = get_db()
        now = datetime.now(timezone.utc).isoformat()
        db.execute("UPDATE sessions SET title = ?, updated_at = ? WHERE id = ?", (title, now, session_id))
        db.commit()

    def delete_session(self, session_id: str):
        db = get_db()
        db.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
        db.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        db.commit()

    def add_message(self, session_id: str, role: str, content: str, msg_type: str = "text", metadata: dict = None) -> dict:
        logger.debug(f"添加消息到会话 {session_id}, 角色: {role}, 内容长度: {len(content)}")
        db = get_db()
        msg_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        metadata_json = json.dumps(metadata, ensure_ascii=False) if metadata else None
        db.execute(
            "INSERT INTO messages (id, session_id, role, content, msg_type, metadata_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (msg_id, session_id, role, content, msg_type, metadata_json, now)
        )
        if role == "user":
            count = db.execute("SELECT COUNT(*) FROM messages WHERE session_id = ? AND role = 'user'", (session_id,)).fetchone()[0]
            if count <= 1:
                title = content[:50] + ("..." if len(content) > 50 else "")
                logger.info(f"更新会话标题: {session_id} -> {title[:30]}...")
                db.execute("UPDATE sessions SET title = ?, updated_at = ? WHERE id = ?", (title, now, session_id))
            else:
                db.execute("UPDATE sessions SET updated_at = ? WHERE id = ?", (now, session_id))
        db.commit()
        logger.debug(f"消息添加成功: {msg_id}")
        return {"id": msg_id, "session_id": session_id, "role": role, "content": content, "msg_type": msg_type, "metadata": metadata, "created_at": now}

    def get_messages(self, session_id: str) -> List[dict]:
        db = get_db()
        rows = db.execute(
            "SELECT id, session_id, role, content, msg_type, metadata_json, created_at FROM messages WHERE session_id = ? ORDER BY created_at",
            (session_id,)
        ).fetchall()
        messages = []
        for row in rows:
            msg = dict(row)
            msg["metadata"] = json.loads(msg["metadata_json"]) if msg["metadata_json"] else None
            del msg["metadata_json"]
            messages.append(msg)
        return messages


session_service = SessionService()

from datetime import datetime, timezone
from typing import Optional
from app.core.database import get_db


class UserService:
    def get_profile(self, user_id: str) -> dict:
        db = get_db()
        row = db.execute("SELECT * FROM user_profiles WHERE user_id = ?", (user_id,)).fetchone()
        if row:
            return dict(row)
        return self._create_default_profile(user_id)

    def _create_default_profile(self, user_id: str) -> dict:
        db = get_db()
        now = datetime.now(timezone.utc).isoformat()
        profile = {
            "user_id": user_id,
            "display_name": f"User_{user_id[:8]}",
            "avatar_url": "",
            "research_field": "",
            "knowledge_level": "intermediate",
            "institution": "",
            "bio": "",
            "model_mode": "free",
            "balance": 0.0,
            "created_at": now,
            "updated_at": now,
        }
        db.execute(
            "INSERT INTO user_profiles (user_id, display_name, avatar_url, research_field, knowledge_level, institution, bio, model_mode, balance, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (user_id, profile["display_name"], "", "", "intermediate", "", "", "free", 0.0, now, now)
        )
        db.commit()
        return profile

    def update_profile(self, user_id: str, updates: dict) -> dict:
        db = get_db()
        self.get_profile(user_id)  # 确保存在
        now = datetime.now(timezone.utc).isoformat()
        allowed_fields = ["display_name", "avatar_url", "research_field", "knowledge_level", "institution", "bio", "model_mode"]
        set_parts = []
        values = []
        for k, v in updates.items():
            if k in allowed_fields and v is not None:
                set_parts.append(f"{k} = ?")
                values.append(v)
        if set_parts:
            set_parts.append("updated_at = ?")
            values.append(now)
            values.append(user_id)
            db.execute(f"UPDATE user_profiles SET {', '.join(set_parts)} WHERE user_id = ?", values)
            db.commit()
        return self.get_profile(user_id)


user_service = UserService()

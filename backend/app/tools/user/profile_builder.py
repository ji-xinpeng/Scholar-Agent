from typing import Dict, Any, Optional
from app.tools.base import BaseTool
from app.application.services.user_service import user_service


class ProfileTool(BaseTool):
    name = "ProfileTool"
    description = "查询用户资料，包括研究领域、知识水平、机构等信息。可以帮助其他工具更好地定制搜索、筛选和总结内容。"
    parameters = {
        "user_id": {"type": "string", "description": "用户ID", "required": True}
    }

    async def run(self, **kwargs) -> Dict[str, Any]:
        """查询用户资料"""
        user_id = kwargs.get("user_id", "")
        
        if not user_id:
            return {
                "success": False,
                "error": "缺少 user_id 参数"
            }
        
        profile = user_service.get_profile(user_id)
        
        return {
            "success": True,
            "user_id": user_id,
            "profile": {
                "display_name": profile.get("display_name", ""),
                "research_field": profile.get("research_field", ""),
                "knowledge_level": profile.get("knowledge_level", "intermediate"),
                "institution": profile.get("institution", ""),
                "bio": profile.get("bio", "")
            }
        }

    def resolve_params(self, params: Dict[str, Any], previous_results: Dict[str, Any]) -> Dict[str, Any]:
        """自动解析参数"""
        return params

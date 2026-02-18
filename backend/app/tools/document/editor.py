from typing import Dict, Any
from app.tools.base import BaseTool
from app.application.services.document_service import document_service
from app.infrastructure.logging.config import logger


class DocEditTool(BaseTool):
    """对文档进行增删改查操作"""
    name = "DocEditTool"
    description = "对文档进行读取、修改、追加、替换、新建或删除操作。仅支持 .docx/.doc、.md、.txt 格式。read/update/append/replace/delete 需要 doc_id（从用户选中列表取）；create 需要 filename，可同时设置 content 作为初始内容。"
    parameters = {
        "action": {
            "type": "string",
            "description": "操作类型: read=读取全文, update=全文替换, append=末尾追加, replace=替换指定片段, create=新建文档, delete=删除文档",
            "required": True
        },
        "doc_id": {"type": "string", "description": "文档ID（read/update/append/replace/delete 时必填）", "required": False},
        "content": {"type": "string", "description": "新内容（create/update/append 时必填）", "default": ""},
        "old_text": {"type": "string", "description": "要替换的原文（replace 时必填）", "default": ""},
        "new_text": {"type": "string", "description": "替换后的内容（replace 时必填，空字符串表示删除）", "default": ""},
        "filename": {"type": "string", "description": "文件名（create 时必填）", "default": ""},
        "file_type": {"type": "string", "description": "文件类型（create 时可选）: markdown/text/word", "default": "markdown"},
        "user_id": {"type": "string", "description": "用户ID（系统自动填充，无需指定）", "required": False}
    }

    def get_action_label(self, params: Dict[str, Any]) -> str:
        action = params.get("action", "")
        if action == "create":
            filename = params.get("filename", "新文档")
            return f"创建文档: {filename}"
        elif action == "delete":
            return "删除文档"
        elif action == "read":
            return "读取文档"
        elif action == "update":
            return "更新文档内容"
        elif action == "append":
            return "追加文档内容"
        elif action == "replace":
            return "替换文档内容"
        return super().get_action_label(params)

    async def run(self, **kwargs) -> Dict[str, Any]:
        action = kwargs.get("action", "").lower()
        doc_id = kwargs.get("doc_id", "")
        content = kwargs.get("content", "")
        old_text = kwargs.get("old_text", "")
        new_text = kwargs.get("new_text", "")
        filename = kwargs.get("filename", "")
        file_type = kwargs.get("file_type", "markdown")
        user_id = kwargs.get("user_id", "")

        try:
            if action == "create":
                if not filename:
                    return {"success": False, "error": "create 操作需要提供 filename"}
                if not user_id:
                    return {"success": False, "error": "create 操作需要提供 user_id"}
                doc = document_service.create_document(user_id, filename, content, file_type)
                return {"success": True, "action": "create", "doc_id": doc["id"], "filename": filename, "message": "文档创建成功"}
            
            if action == "delete":
                if not doc_id:
                    return {"success": False, "error": "delete 操作需要提供 doc_id"}
                ok = document_service.delete_document(doc_id)
                return {"success": ok, "action": "delete", "message": "文档已删除" if ok else "删除失败"}
            
            doc = document_service.get_document(doc_id)
            if not doc:
                return {"success": False, "error": f"文档不存在: {doc_id}"}

            file_type = doc.get("file_type", "")
            if file_type not in ("word", "markdown", "text"):
                return {"success": False, "error": f"该文档格式({file_type})不支持编辑，仅支持 word/markdown/text"}

            if action == "read":
                text = document_service.get_document_content(doc_id)
                return {"success": True, "action": "read", "content": text or "", "filename": doc.get("original_name", "")}
            elif action == "update":
                ok = document_service.update_document_content(doc_id, content)
                return {"success": ok, "action": "update", "message": "全文已更新" if ok else "更新失败"}
            elif action == "append":
                ok = document_service.append_document_content(doc_id, content)
                return {"success": ok, "action": "append", "message": "内容已追加" if ok else "追加失败"}
            elif action == "replace":
                ok = document_service.replace_document_content(doc_id, old_text, new_text)
                return {"success": ok, "action": "replace", "message": "内容已替换" if ok else "替换失败（可能原文不存在）"}
            else:
                return {"success": False, "error": f"未知操作: {action}，支持 read/update/append/replace/create/delete"}
        except Exception as e:
            logger.error(f"DocEditTool 执行失败: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

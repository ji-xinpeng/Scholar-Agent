from typing import Dict, Any
from app.tools.base import BaseTool
from app.application.services.document_service import document_service


class DocEditTool(BaseTool):
    """对选中文档进行增删改查，仅支持 word、markdown、text 格式"""
    name = "DocEditTool"
    description = "对用户选中的文档进行读取、修改、追加或替换内容。仅支持 .docx/.doc、.md、.txt 格式。"
    parameters = {
        "action": {
            "type": "string",
            "description": "操作类型: read=读取全文, update=全文替换, append=末尾追加, replace=替换指定片段",
            "required": True
        },
        "doc_id": {"type": "string", "description": "文档ID，从用户选中的文档列表中获取", "required": True},
        "content": {"type": "string", "description": "新内容（update/append 时必填）", "default": ""},
        "old_text": {"type": "string", "description": "要替换的原文（replace 时必填）", "default": ""},
        "new_text": {"type": "string", "description": "替换后的内容（replace 时必填，空字符串表示删除）", "default": ""}
    }

    async def run(self, **kwargs) -> Dict[str, Any]:
        action = kwargs.get("action", "").lower()
        doc_id = kwargs.get("doc_id", "")
        content = kwargs.get("content", "")
        old_text = kwargs.get("old_text", "")
        new_text = kwargs.get("new_text", "")

        doc = document_service.get_document(doc_id)
        if not doc:
            return {"success": False, "error": f"文档不存在: {doc_id}"}

        file_type = doc.get("file_type", "")
        if file_type not in ("word", "markdown", "text"):
            return {"success": False, "error": f"该文档格式({file_type})不支持编辑，仅支持 word/markdown/text"}

        try:
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
                return {"success": False, "error": f"未知操作: {action}，支持 read/update/append/replace"}
        except Exception as e:
            return {"success": False, "error": str(e)}

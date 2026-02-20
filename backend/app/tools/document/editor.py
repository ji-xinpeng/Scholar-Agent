from typing import Dict, Any
from app.tools.base import BaseTool
from app.application.services.document_service import document_service
from app.infrastructure.logging.config import logger


class DocEditTool(BaseTool):
    """对文档进行增删改查操作"""
    name = "DocEditTool"
    description = "对文档进行读取、修改、追加、替换、新建或删除操作。仅支持 .docx/.doc、.md、.txt 格式。read/update/append/replace/delete 需要 doc_id（从用户选中列表取）；create 需要 filename，可同时设置 content 作为初始内容。"
    usage_hint = """如果用户选中了文档，优先使用选中的 doc_id。
    - 编辑文档前必须先用 read 操作读取完整内容
    - 删除或修改段落时，old_text 要包含完整段落，不能只匹配一句话
    - 删除内容时 new_text 设为空字符串，修改时 new_text 设为完整新内容"""
    examples = """**示例：删除文档中的某一段**
    <question>把文档中描述垂直场景应用研究这一段都删掉</question>
    <thought>我需要先读取文档内容，找到要删除的段落，然后删除它。</thought>
    <action>DocEditTool(action="read", doc_id="doc-123", user_id="user-123")</action>
    <observation>{"success": true, "content": "### 学术文献综合总结\\n本次整理的10篇学术文献...\\n#### 二、垂直场景应用研究\\n1. 工业与数字孪生...\\n#### 整体趋势与说明..."}</observation>
    <thought>我已经读取了文档内容，现在删除"垂直场景应用研究"这一整段。我会提供完整的段落内容作为 old_text，确保唯一匹配。</thought>
    <action>DocEditTool(action="replace", doc_id="doc-123", old_text="#### 二、垂直场景应用研究\\n1. 工业与数字孪生：...", new_text="", user_id="user-123")</action>
    <observation>{"success": true, "message": "内容已替换"}</observation>
    <thought>段落已成功删除，任务完成。</thought>
    <final_answer>已成功删除文档中描述垂直场景应用研究的段落。</final_answer>"""
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

    def resolve_params(self, params: Dict[str, Any], previous_results: Dict[str, Any]) -> Dict[str, Any]:
        params = dict(params) if params else {}
        action = params.get("action", "")
        summary = previous_results.get("SummarizeTool", {}).get("summary", "")
        if summary:
            params["content"] = summary
        
        # 如果是创建、更新或追加操作，且没有提供 content，尝试从 SummarizeTool 或其他工具的结果中获取
        if action in ("create", "update", "append") and not params.get("content"):
            for prev_tool in ("SummarizeTool",):
                if prev_tool in previous_results:
                    prev_result = previous_results[prev_tool]
                    if isinstance(prev_result, dict) and prev_result.get("success"):
                        summary = prev_result.get("summary")
                        if summary:
                            params["content"] = summary
                            logger.info(f"{self.name} 自动使用 {prev_tool} 的结果作为 content")
                            break
        
        return params

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
                
                # 从文件名推断文件类型
                ext_to_type = {
                    ".md": "markdown",
                    ".markdown": "markdown",
                    ".txt": "text",
                    ".docx": "word",
                    ".doc": "word"
                }
                import os
                ext = os.path.splitext(filename)[1].lower()
                if ext in ext_to_type:
                    file_type = ext_to_type[ext]
                
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
                return {"success": True, "action": "read", "content": text or "", "filename": doc.get("original_name", ""), "doc_id": doc_id}
            elif action == "update":
                ok = document_service.update_document_content(doc_id, content)
                return {"success": ok, "action": "update", "message": "全文已更新" if ok else "更新失败", "doc_id": doc_id}
            elif action == "append":
                ok = document_service.append_document_content(doc_id, content)
                return {"success": ok, "action": "append", "message": "内容已追加" if ok else "追加失败", "doc_id": doc_id}
            elif action == "replace":
                ok = document_service.replace_document_content(doc_id, old_text, new_text)
                return {"success": ok, "action": "replace", "message": "内容已替换" if ok else "替换失败（可能原文不存在）", "doc_id": doc_id}
            else:
                return {"success": False, "error": f"未知操作: {action}，支持 read/update/append/replace/create/delete"}
        except Exception as e:
            logger.error(f"DocEditTool 执行失败: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

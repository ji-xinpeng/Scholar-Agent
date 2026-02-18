from typing import Dict, Any, List
from app.tools.base import BaseTool
from app.application.services.document_service import document_service
from app.infrastructure.llm.base import MessageRole, ChatMessage
from app.infrastructure.llm.service import llm_service


class MultiModalRAGTool(BaseTool):
    name = "MultiModalRAGTool"
    description = "基于上传文档进行多模态问答"
    parameters = {
        "query": {"type": "string", "description": "用户问题", "required": True},
        "document_ids": {"type": "array", "description": "指定文档ID列表", "default": []},
        "top_k": {"type": "integer", "description": "返回最相关的 k 个片段", "default": 5}
    }

    async def run(self, **kwargs) -> Dict[str, Any]:
        """基于文档的 RAG 检索"""
        query = kwargs.get("query", "")
        document_ids = kwargs.get("document_ids", [])
        top_k = kwargs.get("top_k", 5)
        
        if not query:
            return {
                "success": False,
                "error": "请提供查询问题"
            }

        try:
            document_contents = []
            sources = []
            
            if document_ids and isinstance(document_ids, list):
                for doc_id in document_ids:
                    doc = document_service.get_document(doc_id)
                    if doc:
                        content = document_service.get_document_content(doc_id)
                        if content:
                            document_contents.append({
                                "doc_id": doc_id,
                                "title": doc.get("original_name", "未知文档"),
                                "content": content
                            })
                            sources.append(doc.get("original_name", "未知文档"))
            
            if not document_contents:
                return {
                    "success": False,
                    "error": "没有找到可用的文档内容",
                    "query": query,
                    "document_ids": document_ids
                }

            context_text = "\n\n".join([
                f"=== 文档: {d['title']} ===\n{d['content']}"
                for d in document_contents
            ])

            prompt = f"""请基于以下文档内容回答用户问题。如果文档中没有相关信息，请诚实地说明。

文档内容:
{context_text}

用户问题: {query}
"""
            messages = [ChatMessage(role=MessageRole.USER, content=prompt)]
            response = await llm_service.chat(messages, temperature=0.7)
            
            return {
                "success": True,
                "query": query,
                "document_ids": document_ids,
                "top_k": top_k,
                "answer": response.content,
                "sources": sources,
                "documents_used": len(document_contents)
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"文档检索失败: {str(e)}",
                "query": query,
                "document_ids": document_ids
            }

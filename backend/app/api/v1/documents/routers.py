from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Query
from typing import Optional
from app.schemas import FolderCreate
from app.application.services.document_service import document_service
from app.infrastructure.storage.database.connection import get_db

router = APIRouter()


def verify_document_ownership(doc_id: str, user_id: str):
    """验证用户是否拥有该文档的访问权限（本地开发环境暂时跳过严格验证）"""
    doc = document_service.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


def verify_folder_ownership(folder_id: str, user_id: str):
    """验证用户是否拥有该文件夹的访问权限（本地开发环境暂时跳过严格验证）"""
    db = get_db()
    row = db.execute("SELECT * FROM folders WHERE id = ?", (folder_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Folder not found")
    folder = dict(row)
    return folder


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    user_id: str = Form(default="default"),
    folder_id: Optional[str] = Form(default=None),
):
    """上传文档（支持PDF、Word、Markdown等格式）。"""
    content = await file.read()
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Empty file")
    if len(content) > 100 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (max 100MB)")

    result = document_service.upload_document(user_id, file.filename, content, folder_id)
    return result


@router.get("/")
async def list_documents(
    user_id: str = Query(default="default"),
    folder_id: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
):
    return document_service.list_documents(user_id, folder_id, page, page_size)


@router.get("/{doc_id}")
async def get_document(doc_id: str, user_id: str = Query(default="default")):
    verify_document_ownership(doc_id, user_id)
    doc = document_service.get_document(doc_id)
    return doc


@router.get("/{doc_id}/content")
async def get_document_content(doc_id: str, user_id: str = Query(default="default")):
    verify_document_ownership(doc_id, user_id)
    content = document_service.get_document_content(doc_id)
    if content is None:
        raise HTTPException(status_code=404, detail="Document not found or unsupported format")
    return {"content": content}


@router.put("/{doc_id}/content")
async def update_document_content(doc_id: str, body: dict, user_id: str = Query(default="default")):
    """更新文档内容（支持 word、markdown、text 格式）"""
    verify_document_ownership(doc_id, user_id)
    content = body.get("content")
    if content is None:
        raise HTTPException(status_code=400, detail="content is required")
    ok = document_service.update_document_content(doc_id, content)
    if not ok:
        raise HTTPException(status_code=404, detail="Document not found or unsupported format for editing")
    return {"status": "ok", "content": content}


@router.delete("/{doc_id}")
async def delete_document(doc_id: str, user_id: str = Query(default="default")):
    verify_document_ownership(doc_id, user_id)
    ok = document_service.delete_document(doc_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"status": "ok"}


@router.put("/{doc_id}/move")
async def move_document(doc_id: str, folder_id: Optional[str] = None, user_id: str = Query(default="default")):
    verify_document_ownership(doc_id, user_id)
    document_service.move_document(doc_id, folder_id)
    return {"status": "ok"}


@router.post("/folders")
async def create_folder(request: FolderCreate):
    return document_service.create_folder(request.user_id, request.name, request.parent_id)


@router.get("/folders/list")
async def list_folders(user_id: str = Query(default="default")):
    return {"folders": document_service.list_folders(user_id)}


@router.delete("/folders/{folder_id}")
async def delete_folder(folder_id: str, user_id: str = Query(default="default")):
    verify_folder_ownership(folder_id, user_id)
    document_service.delete_folder(folder_id)
    return {"status": "ok"}

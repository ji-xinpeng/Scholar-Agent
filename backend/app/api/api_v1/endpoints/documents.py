from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Query
from typing import Optional
from app.models.schemas import FolderCreate
from app.services.document_service import document_service

router = APIRouter()


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
async def get_document(doc_id: str):
    doc = document_service.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.get("/{doc_id}/content")
async def get_document_content(doc_id: str):
    content = document_service.get_document_content(doc_id)
    if content is None:
        raise HTTPException(status_code=404, detail="Document not found or unsupported format")
    return {"content": content}


@router.delete("/{doc_id}")
async def delete_document(doc_id: str):
    ok = document_service.delete_document(doc_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"status": "ok"}


@router.put("/{doc_id}/move")
async def move_document(doc_id: str, folder_id: Optional[str] = None):
    document_service.move_document(doc_id, folder_id)
    return {"status": "ok"}


# ======== 文件夹 ========
@router.post("/folders")
async def create_folder(request: FolderCreate):
    return document_service.create_folder(request.user_id, request.name, request.parent_id)


@router.get("/folders/list")
async def list_folders(user_id: str = Query(default="default")):
    return {"folders": document_service.list_folders(user_id)}


@router.delete("/folders/{folder_id}")
async def delete_folder(folder_id: str):
    document_service.delete_folder(folder_id)
    return {"status": "ok"}

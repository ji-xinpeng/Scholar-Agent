from fastapi import APIRouter, Query
from app.schemas import UserProfileUpdate
from app.application.services.user_service import user_service

router = APIRouter()


@router.get("/profile")
async def get_profile(user_id: str = Query(default="default")):
    return user_service.get_profile(user_id)


@router.put("/profile")
async def update_profile(user_id: str = Query(default="default"), body: UserProfileUpdate = None):
    updates = body.model_dump(exclude_none=True) if body else {}
    return user_service.update_profile(user_id, updates)

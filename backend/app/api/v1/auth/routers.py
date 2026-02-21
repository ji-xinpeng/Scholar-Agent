from fastapi import APIRouter, HTTPException
from app.schemas import LoginRequest, RegisterRequest, AuthResponse
from app.application.services.auth_service import auth_service

router = APIRouter()


@router.post("/login", response_model=AuthResponse)
async def login(body: LoginRequest):
    try:
        result = auth_service.login(body.username, body.password)
        return AuthResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/register", response_model=AuthResponse)
async def register(body: RegisterRequest):
    try:
        result = auth_service.register(body.username, body.password, body.confirm_password)
        return AuthResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

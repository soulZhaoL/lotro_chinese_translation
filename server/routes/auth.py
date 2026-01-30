# 认证相关路由。
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from ..services import auth as auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/login")
def login(request: LoginRequest):
    """用户登录，返回 token 与权限信息。"""
    try:
        return auth_service.issue_login_response(request.username, request.password)
    except auth_service.AuthError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

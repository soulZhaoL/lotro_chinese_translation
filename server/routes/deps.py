# 路由依赖项与鉴权。
from typing import Dict

from fastapi import Depends, Header, HTTPException, status

from ..services import auth as auth_service


def require_auth(authorization: str = Header(..., alias="Authorization")) -> Dict[str, int]:
    """鉴权依赖：校验 Bearer token 并返回用户信息。"""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="缺少 Bearer token")
    token = authorization.removeprefix("Bearer ").strip()
    try:
        payload = auth_service.verify_token(token)
    except auth_service.AuthError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    userId = payload.get("sub")
    if not isinstance(userId, int):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="token 无效")

    user = auth_service.get_user_by_id(userId)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在")

    return {"userId": userId, "username": user["username"]}

# 路由依赖项与鉴权。
from typing import Any, Dict, Optional, Tuple

from fastapi import Header, HTTPException, Request, status

from ..logging_context import update_log_user
from ..services import auth as auth_service


def _resolve_user_from_authorization(authorization: str) -> Dict[str, int]:
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


def try_resolve_auth_user(authorization: Optional[str]) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    if authorization is None or authorization.strip() == "":
        return None, None
    try:
        return _resolve_user_from_authorization(authorization), None
    except HTTPException as exc:
        detail = str(exc.detail) if exc.detail else "鉴权失败"
        return None, detail


def require_auth(request: Request, authorization: str = Header(..., alias="Authorization")) -> Dict[str, int]:
    """鉴权依赖：校验 Bearer token 并返回用户信息。"""
    request_user = getattr(request.state, "auth_user", None)
    if request_user is not None:
        update_log_user(request_user)
        return request_user

    user = _resolve_user_from_authorization(authorization)
    request.state.auth_user = user
    update_log_user(user)
    return user

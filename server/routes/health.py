# 健康检查路由。
from fastapi import APIRouter

from ..response import success_response

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
def health_check():
    """服务健康检查。"""
    return success_response({"status": "ok"})

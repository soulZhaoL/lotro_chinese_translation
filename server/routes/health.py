# 健康检查路由。
from fastapi import APIRouter

from ..response import success_response
from ..services.maintenance import get_maintenance_state

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
def health_check():
    """服务健康检查。"""
    return success_response({"status": "ok", "maintenance": get_maintenance_state()})

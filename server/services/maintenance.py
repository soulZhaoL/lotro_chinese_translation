# 维护模式配置与判定。
from typing import Any, Dict, Iterable, List

from ..config import get_config
from ..response import error_response

_DEFAULT_MESSAGE = "系统维护中，请稍后再试"


def _resolve_message(message: Any) -> str:
    if isinstance(message, str) and message.strip():
        return message
    return _DEFAULT_MESSAGE


def get_maintenance_config() -> Dict[str, Any]:
    config = get_config()
    return config["maintenance"]


def get_maintenance_state() -> Dict[str, Any]:
    maintenance = get_maintenance_config()
    message = _resolve_message(maintenance.get("message"))
    return {"enabled": bool(maintenance.get("enabled")), "message": message}


def is_maintenance_enabled() -> bool:
    return bool(get_maintenance_config().get("enabled"))


def get_allow_paths() -> List[str]:
    allow_paths = get_maintenance_config().get("allow_paths") or []
    return list(allow_paths)


def is_path_allowed(path: str, allow_paths: Iterable[str]) -> bool:
    for item in allow_paths:
        if path == item or path.startswith(f"{item}/"):
            return True
    return False


def build_maintenance_response():
    state = get_maintenance_state()
    return error_response(
        state["message"],
        status_code=503,
        code="MAINTENANCE",
        data={"maintenance": state},
    )

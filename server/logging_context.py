# 请求级日志上下文。
from contextvars import ContextVar, Token
from typing import Any, Dict, Optional


LogContext = Dict[str, str]

_DEFAULT_LOG_CONTEXT: LogContext = {
    "requestId": "-",
    "userId": "-",
    "username": "-",
    "clientIp": "-",
}
_log_context_var: ContextVar[LogContext] = ContextVar("log_context", default=_DEFAULT_LOG_CONTEXT.copy())


def set_log_context(request_id: str, client_ip: str) -> Token[LogContext]:
    context = _DEFAULT_LOG_CONTEXT.copy()
    context["requestId"] = request_id
    context["clientIp"] = client_ip
    return _log_context_var.set(context)


def update_log_user(user: Optional[Dict[str, Any]]) -> None:
    context = _log_context_var.get().copy()
    if user is None:
        context["userId"] = "-"
        context["username"] = "-"
    else:
        user_id = user.get("userId", user.get("id"))
        username = user.get("username")
        context["userId"] = str(user_id) if user_id is not None else "-"
        context["username"] = str(username) if username else "-"
    _log_context_var.set(context)


def get_log_context() -> LogContext:
    return _log_context_var.get().copy()


def reset_log_context(token: Token[LogContext]) -> None:
    _log_context_var.reset(token)

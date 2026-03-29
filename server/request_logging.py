# 请求日志拦截与脱敏工具。
import json
import uuid
from typing import Any, Dict, Optional
from urllib.parse import parse_qs

from fastapi import Request
from loguru import logger

from .config import get_config


def _get_logging_config() -> Dict[str, Any]:
    return get_config()["logging"]


def create_request_id() -> str:
    return uuid.uuid4().hex


def get_client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        client_ip = forwarded_for.split(",")[0].strip()
        if client_ip:
            return client_ip
    if request.client and request.client.host:
        return request.client.host
    return "-"


def _is_sensitive_key(key: str, redact_fields: set[str]) -> bool:
    normalized = key.strip().lower()
    return normalized in redact_fields


def _truncate_text(value: str, max_length: int) -> str:
    if len(value) <= max_length:
        return value
    return f"{value[:max_length]}...(truncated)"


def sanitize_payload(value: Any, redact_fields: set[str], max_body_length: int, key: Optional[str] = None) -> Any:
    if key and _is_sensitive_key(key, redact_fields):
        return "***"
    if isinstance(value, dict):
        return {
            str(item_key): sanitize_payload(item_value, redact_fields, max_body_length, str(item_key))
            for item_key, item_value in value.items()
        }
    if isinstance(value, list):
        return [sanitize_payload(item, redact_fields, max_body_length) for item in value]
    if isinstance(value, tuple):
        return [sanitize_payload(item, redact_fields, max_body_length) for item in value]
    if isinstance(value, str):
        return _truncate_text(value, max_body_length)
    return value


def sanitize_query_params(request: Request) -> Dict[str, Any]:
    logging_config = _get_logging_config()
    redact_fields = {str(item).lower() for item in logging_config["redact_fields"]}
    max_body_length = logging_config["request_max_body_length"]
    grouped: Dict[str, list[str]] = {}
    for key, value in request.query_params.multi_items():
        grouped.setdefault(key, []).append(value)

    normalized: Dict[str, Any] = {}
    for key, values in grouped.items():
        normalized[key] = values[0] if len(values) == 1 else values
    return sanitize_payload(normalized, redact_fields, max_body_length)


async def extract_request_body(request: Request) -> Optional[Any]:
    logging_config = _get_logging_config()
    log_body_methods = {str(item).upper() for item in logging_config["log_body_methods"]}
    if request.method.upper() not in log_body_methods:
        return None

    body = await request.body()
    if not body:
        return None

    max_body_length = logging_config["request_max_body_length"]
    redact_fields = {str(item).lower() for item in logging_config["redact_fields"]}
    content_type = request.headers.get("content-type", "")

    if content_type.startswith("application/json"):
        try:
            parsed = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return {
                "contentType": content_type,
                "bodyBytes": len(body),
                "bodyPreview": _truncate_text(body.decode("utf-8", errors="replace"), max_body_length),
            }
        return sanitize_payload(parsed, redact_fields, max_body_length)

    if content_type.startswith("application/x-www-form-urlencoded"):
        parsed = parse_qs(body.decode("utf-8"), keep_blank_values=True)
        normalized: Dict[str, Any] = {}
        for key, values in parsed.items():
            normalized[key] = values[0] if len(values) == 1 else values
        return sanitize_payload(normalized, redact_fields, max_body_length)

    if content_type.startswith("multipart/form-data"):
        return {
            "contentType": content_type,
            "bodyBytes": len(body),
            "bodySummary": "<multipart omitted>",
        }

    return {
        "contentType": content_type or "application/octet-stream",
        "bodyBytes": len(body),
        "bodyPreview": _truncate_text(body.decode("utf-8", errors="replace"), max_body_length),
    }


def log_request_start(request: Request, request_body: Optional[Any], auth_error: Optional[str]) -> None:
    logger.info(
        "HTTP request start: method={} path={} query={} body={} authError={} userAgent={}",
        request.method,
        request.url.path,
        sanitize_query_params(request),
        request_body,
        auth_error,
        request.headers.get("User-Agent", "-"),
    )


def log_request_end(request: Request, status_code: int, elapsed_ms: float) -> None:
    logger.info(
        "HTTP request end: method={} path={} statusCode={} elapsedMs={:.0f}",
        request.method,
        request.url.path,
        status_code,
        elapsed_ms,
    )

# 请求日志工具测试。
import asyncio

import pytest
from starlette.requests import Request

from server.request_logging import extract_request_body, sanitize_payload


@pytest.mark.no_db
def test_sanitize_payload_masks_sensitive_fields():
    payload = {
        "username": "tester",
        "password": "secret123",
        "nested": {
            "token": "abc123",
            "plain": "value",
        },
    }

    sanitized = sanitize_payload(payload, {"password", "token"}, 128)

    assert sanitized["username"] == "tester"
    assert sanitized["password"] == "***"
    assert sanitized["nested"]["token"] == "***"
    assert sanitized["nested"]["plain"] == "value"


@pytest.mark.no_db
def test_sanitize_payload_truncates_long_text():
    sanitized = sanitize_payload({"message": "x" * 20}, set(), 8)
    assert sanitized["message"] == "xxxxxxxx...(truncated)"


@pytest.mark.no_db
def test_extract_request_body_masks_json_fields():
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/auth/login",
        "headers": [(b"content-type", b"application/json")],
        "query_string": b"",
        "client": ("127.0.0.1", 12345),
    }

    async def receive():
        return {
            "type": "http.request",
            "body": b'{"username":"tester","password":"secret123"}',
            "more_body": False,
        }

    request = Request(scope, receive)
    body = asyncio.run(extract_request_body(request))

    assert body == {"username": "tester", "password": "***"}


@pytest.mark.no_db
def test_extract_request_body_omits_multipart_content():
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/texts/upload",
        "headers": [(b"content-type", b"multipart/form-data; boundary=abc")],
        "query_string": b"",
        "client": ("127.0.0.1", 12345),
    }

    async def receive():
        return {
            "type": "http.request",
            "body": b"--abc\r\nbinary-content\r\n--abc--",
            "more_body": False,
        }

    request = Request(scope, receive)
    body = asyncio.run(extract_request_body(request))

    assert body["bodySummary"] == "<multipart omitted>"
    assert body["bodyBytes"] > 0

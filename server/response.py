# 统一响应封装。
from typing import Any, Optional

from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse


def success_response(
    data: Any,
    message: str = "操作成功",
    code: str = "0000",
    status_code: int = 200,
) -> JSONResponse:
    content = {
        "success": True,
        "statusCode": status_code,
        "code": code,
        "message": message,
        "data": data,
    }
    return JSONResponse(status_code=status_code, content=jsonable_encoder(content))


def error_response(
    message: str,
    status_code: int,
    code: Optional[str] = None,
    data: Any = None,
) -> JSONResponse:
    resolved_code = code if code is not None else f"{status_code:04d}"
    content = {
        "success": False,
        "statusCode": status_code,
        "code": resolved_code,
        "message": message,
        "data": data,
    }
    return JSONResponse(status_code=status_code, content=jsonable_encoder(content))

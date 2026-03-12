# FastAPI 应用入口与路由注册。
import time

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from .config import get_config
from .logger import setup_logger
from .response import error_response
from .routes import auth, changes, claims, dictionary, health, locks, texts, validate
from .services.maintenance import build_maintenance_response, get_allow_paths, is_maintenance_enabled, is_path_allowed


def create_app() -> FastAPI:
    setup_logger()

    config = get_config()
    app = FastAPI(title="LOTRO Translation API")

    cors_config = config["cors"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_config["allow_origins"],
        allow_methods=cors_config["allow_methods"],
        allow_headers=cors_config["allow_headers"],
        allow_credentials=cors_config["allow_credentials"],
        expose_headers=cors_config["expose_headers"],
        max_age=cors_config["max_age"],
    )

    app.add_middleware(GZipMiddleware, minimum_size=config["http"]["gzip_minimum_size"])

    @app.middleware("http")
    async def logging_middleware(request: Request, call_next):
        method = request.method
        path = request.url.path
        query = request.url.query
        log_path = f"{path}?{query}" if query else path
        logger.info(f"→ {method} {log_path}")

        start = time.monotonic()
        response = await call_next(request)
        elapsed_ms = (time.monotonic() - start) * 1000
        logger.info(f"← {method} {path} {response.status_code} ({elapsed_ms:.0f}ms)")
        return response

    @app.middleware("http")
    async def maintenance_middleware(request: Request, call_next):
        if is_maintenance_enabled():
            path = request.url.path
            if not is_path_allowed(path, get_allow_paths()):
                return build_maintenance_response()
        return await call_next(request)

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        detail = exc.errors()[0]["msg"] if exc.errors() else "请求参数错误"
        logger.warning(f"请求参数校验失败: {detail} | errors={exc.errors()}")
        return error_response(detail, status_code=422)

    @app.exception_handler(HTTPException)
    async def http_exception_handler(req: Request, exc: HTTPException) -> JSONResponse:
        detail = str(exc.detail) if exc.detail else "请求失败"
        if exc.status_code >= 500:
            logger.error(f"HTTP {exc.status_code}: {detail} | {req.method} {req.url.path}")
        elif exc.status_code >= 400:
            logger.warning(f"HTTP {exc.status_code}: {detail} | {req.method} {req.url.path}")
        return error_response(detail, status_code=exc.status_code)

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(req: Request, exc: Exception) -> JSONResponse:
        logger.exception(f"未处理异常: {req.method} {req.url.path} | {exc}")
        return error_response(str(exc) or "服务器内部错误", status_code=500)

    app.include_router(auth.router)
    app.include_router(texts.router)
    app.include_router(claims.router)
    app.include_router(locks.router)
    app.include_router(changes.router)
    app.include_router(dictionary.router)
    app.include_router(health.router)
    app.include_router(validate.router)

    return app


app = create_app()

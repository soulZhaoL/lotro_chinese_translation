# FastAPI 应用入口与路由注册。
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from .config import get_config
from .logger import setup_logger
from .logging_context import reset_log_context, set_log_context, update_log_user
from .request_logging import create_request_id, extract_request_body, get_client_ip, log_request_end, log_request_start
from .response import error_response
from .routes import auth, changes, claims, dictionary, health, locks, texts, validate
from .routes.deps import try_resolve_auth_user
from .services.dictionary_correction_scheduler import start_scheduler, stop_scheduler
from .services.maintenance import build_maintenance_response, get_allow_paths, is_maintenance_enabled, is_path_allowed


@asynccontextmanager
async def lifespan(_: FastAPI):
    start_scheduler()
    try:
        yield
    finally:
        await stop_scheduler()


def _configure_middlewares(app: FastAPI, config) -> None:
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

    _register_logging_middleware(app)
    _register_maintenance_middleware(app)


def _register_logging_middleware(app: FastAPI) -> None:
    @app.middleware("http")
    async def logging_middleware(request: Request, call_next):
        request_id = create_request_id()
        client_ip = get_client_ip(request)
        context_token = set_log_context(request_id, client_ip)
        start = time.monotonic()
        request.state.request_id = request_id

        authorization = request.headers.get("Authorization")
        auth_user, auth_error = try_resolve_auth_user(authorization)
        request.state.auth_user = auth_user
        update_log_user(auth_user)
        request_body = await extract_request_body(request)
        log_request_start(request, request_body, auth_error)

        try:
            response = await call_next(request)
        except Exception:
            elapsed_ms = (time.monotonic() - start) * 1000
            log_request_end(request, 500, elapsed_ms)
            raise
        finally:
            if "response" not in locals():
                reset_log_context(context_token)

        elapsed_ms = (time.monotonic() - start) * 1000
        response.headers["X-Request-Id"] = request_id
        log_request_end(request, response.status_code, elapsed_ms)
        reset_log_context(context_token)
        return response


def _register_maintenance_middleware(app: FastAPI) -> None:
    @app.middleware("http")
    async def maintenance_middleware(request: Request, call_next):
        if is_maintenance_enabled():
            path = request.url.path
            if not is_path_allowed(path, get_allow_paths()):
                return build_maintenance_response()
        return await call_next(request)


async def validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    detail = exc.errors()[0]["msg"] if exc.errors() else "请求参数错误"
    logger.warning(f"请求参数校验失败: {detail} | errors={exc.errors()}")
    return error_response(detail, status_code=422)


async def http_exception_handler(req: Request, exc: HTTPException) -> JSONResponse:
    detail = str(exc.detail) if exc.detail else "请求失败"
    if exc.status_code >= 500:
        logger.error(f"HTTP {exc.status_code}: {detail} | {req.method} {req.url.path}")
    elif exc.status_code >= 400:
        logger.warning(f"HTTP {exc.status_code}: {detail} | {req.method} {req.url.path}")
    return error_response(detail, status_code=exc.status_code)


async def unhandled_exception_handler(req: Request, exc: Exception) -> JSONResponse:
    logger.exception(f"未处理异常: {req.method} {req.url.path} | {exc}")
    return error_response(str(exc) or "服务器内部错误", status_code=500)


def _register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)


def _register_routers(app: FastAPI) -> None:
    app.include_router(auth.router)
    app.include_router(texts.router)
    app.include_router(claims.router)
    app.include_router(locks.router)
    app.include_router(changes.router)
    app.include_router(dictionary.router)
    app.include_router(health.router)
    app.include_router(validate.router)


def create_app() -> FastAPI:
    setup_logger()

    config = get_config()
    app = FastAPI(title="LOTRO Translation API", lifespan=lifespan)

    _configure_middlewares(app, config)
    _register_exception_handlers(app)
    _register_routers(app)

    return app


app = create_app()

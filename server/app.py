# FastAPI 应用入口与路由注册。
from fastapi import FastAPI, Request, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

from .config import get_config
from .response import error_response
from .routes import auth, changes, claims, dictionary, locks, texts, validate


def create_app() -> FastAPI:
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

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        detail = exc.errors()[0]["msg"] if exc.errors() else "请求参数错误"
        return error_response(detail, status_code=422)

    @app.exception_handler(HTTPException)
    async def http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
        detail = str(exc.detail) if exc.detail else "请求失败"
        return error_response(detail, status_code=exc.status_code)

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(_: Request, exc: Exception) -> JSONResponse:
        return error_response(str(exc) or "服务器内部错误", status_code=500)

    app.include_router(auth.router)
    app.include_router(texts.router)
    app.include_router(claims.router)
    app.include_router(locks.router)
    app.include_router(changes.router)
    app.include_router(dictionary.router)
    app.include_router(validate.router)

    return app


app = create_app()

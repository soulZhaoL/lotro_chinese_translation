# FastAPI 应用入口与路由注册。
from fastapi import FastAPI

from .config import get_config
from .routes import auth, changes, claims, dictionary, locks, texts, validate


def create_app() -> FastAPI:
    get_config()
    app = FastAPI(title="LOTRO Translation API")

    app.include_router(auth.router)
    app.include_router(texts.router)
    app.include_router(claims.router)
    app.include_router(locks.router)
    app.include_router(changes.router)
    app.include_router(dictionary.router)
    app.include_router(validate.router)

    return app


app = create_app()

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.router import api_router
from app.api.v1 import OPENAPI_TAGS
from app.contract import CONTRACT_VERSION
from app.core.config import Settings, get_settings
from app.core.db import Database
from app.core.errors import register_exception_handlers
from app.core.openapi import install_openapi_customisation, operation_id
from app.core.request_id import RequestIdMiddleware


def create_app(settings: Settings | None = None) -> FastAPI:
    """Application factory. Run with:  uvicorn app.main:create_app --factory"""
    settings = settings or get_settings()
    database = Database(settings.database_url)

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        yield
        database.dispose()

    app = FastAPI(
        title="MedStock Rural API",
        version=CONTRACT_VERSION,
        lifespan=lifespan,
        openapi_url="/api/v1/openapi.json",
        docs_url=None if settings.app_env == "production" else "/api/v1/docs",
        redoc_url=None,
        generate_unique_id_function=operation_id,
        openapi_tags=OPENAPI_TAGS,
    )
    app.state.settings = settings
    app.state.db = database

    app.add_middleware(RequestIdMiddleware)
    register_exception_handlers(app)
    app.include_router(api_router, prefix="/api/v1")
    if settings.app_env in ("test", "e2e"):
        from app.api.v1.testing import router as test_router

        app.include_router(test_router, prefix="/api/v1")
    install_openapi_customisation(app)
    return app

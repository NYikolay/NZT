from src.api.admin import setup_admin
from src.api.exceptions import (
    app_error_handler,
    validation_exception_handler,
    http_exception_handler,
    unhandled_exception_handler,
)
from src.api.lifetime import lifespan
from src.api.middlewares import RequestContextMiddleware
from src.api.rate_limiter import InMemoryRateLimiter
from src.core.config import settings
from src.core.database import create_engine_from_settings

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from sqlalchemy.ext.asyncio import AsyncEngine

from src.api.routers import get_apps_router
from src.domain.exceptions import BaseAppError


def create_app(engine: AsyncEngine | None = None, **kwargs) -> FastAPI:
    application = FastAPI(
        title=settings.PROJECT_TITLE,
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        lifespan=lifespan,
    )

    if engine is None:
        engine = create_engine_from_settings()
    application.state.engine = engine

    application.add_middleware(
        TrustedHostMiddleware, allowed_hosts=settings.all_hosts_origins
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.all_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        **kwargs,
    )
    application.add_middleware(RequestContextMiddleware)
    application.add_middleware(InMemoryRateLimiter)

    application.include_router(get_apps_router())

    setup_admin(application, engine)

    application.add_exception_handler(BaseAppError, app_error_handler)
    application.add_exception_handler(
        RequestValidationError, validation_exception_handler
    )
    application.add_exception_handler(StarletteHTTPException, http_exception_handler)
    application.add_exception_handler(Exception, unhandled_exception_handler)

    return application


app = create_app()

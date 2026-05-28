from src.core.config import settings

from fastapi import FastAPI

from sqlalchemy.ext.asyncio import AsyncEngine
from src.core.lifetime import lifespan

from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from src.core.routers import get_apps_router


def create_app(engine: AsyncEngine | None = None, **kwargs) -> FastAPI:
    application = FastAPI(
        title=settings.PROJECT_TITLE,
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        lifespan=lifespan,
    )

    if engine:
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

    application.include_router(get_apps_router())

    return application

app = create_app()

from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import create_async_engine

from fastapi import FastAPI

from src.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    engine = getattr(app.state, "engine", None)

    if engine is None:
        engine = create_async_engine(
            url=str(settings.db.SQLALCHEMY_DATABASE_URI), echo=False
        )
        app.state.engine = engine

    try:
        yield
    finally:
        await engine.dispose()

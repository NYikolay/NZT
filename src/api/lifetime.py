from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.core.database import create_engine_from_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    engine = getattr(app.state, "engine", None)

    if engine is None:
        engine = create_engine_from_settings()
        app.state.engine = engine

    try:
        yield
    finally:
        await engine.dispose()

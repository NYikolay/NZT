from contextlib import asynccontextmanager
from logging import getLogger

from fastapi import FastAPI

from src.core.tkq import broker


logger = getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    engine = app.state.engine

    logger.info("Starting Taskiq broker (producer side)...")
    if not broker.is_worker_process:
        await broker.startup()

    try:
        yield
    finally:
        logger.info("Shutting down Taskiq broker...")
        if not broker.is_worker_process:
            await broker.shutdown()

        await engine.dispose()

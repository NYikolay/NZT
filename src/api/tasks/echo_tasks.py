"""Sample task — echoes back the input for testing the Taskiq pipeline."""

from src.api.dependencies import provide_transaction_taskiq
from src.core.tkq import broker
from taskiq import TaskiqDepends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


@broker.task
async def echo_task(
    message: str, session: AsyncSession = TaskiqDepends(provide_transaction_taskiq)
) -> str:
    """Simple echo task to verify the broker/worker pipeline works."""
    print(await session.execute(text("SELECT 'HELLO WORLD'")))
    return f"Echo: {message}"

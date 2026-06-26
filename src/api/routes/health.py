import time
from fastapi import APIRouter
from sqlalchemy import text

from src.api.dependencies import SessionDep
from src.api.schemas.health import HealthResponse

health_router = APIRouter(tags=["health"])

_start_time = time.time()


@health_router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    description="Returns the health status of the service.",
)
async def health_check() -> HealthResponse:
    """Liveness probe."""
    return HealthResponse(
        status="healthy",
        uptime_seconds=time.time() - _start_time,
    )


@health_router.get(
    "/health/ready",
    response_model=HealthResponse,
    summary="Readiness probe",
    description="Checks if the service is ready to accept traffic (includes DB check).",
)
async def readiness_check(session: SessionDep) -> HealthResponse:
    """Readiness probe — checks database connectivity."""
    db_status = "unhealthy"
    try:
        result = await session.execute(text("SELECT 1"))
        if result.scalar() == 1:
            db_status = "healthy"
    except Exception:
        db_status = "unhealthy"

    return HealthResponse(
        status="healthy" if db_status == "healthy" else "degraded",
        database=db_status,
        uptime_seconds=time.time() - _start_time,
    )

"""Taskiq configuration — NATS broker with Redis result backend."""

from taskiq import TaskiqScheduler
from taskiq_nats import NatsBroker
from taskiq_redis import RedisAsyncResultBackend, RedisScheduleSource
from taskiq.schedule_sources import LabelScheduleSource
from taskiq_fastapi import init

from src.core.config import settings


def create_broker() -> NatsBroker:
    """Build and return a configured NATS broker with Redis result backend."""
    nats_url = f"nats://{settings.nats.host}:{settings.nats.port}"

    result_backend = RedisAsyncResultBackend(
        redis_url=f"redis://{settings.redis.host}:{settings.redis.port}/{settings.redis.db}",
    )

    broker = NatsBroker(
        servers=nats_url,
        queue="nzt-tasks",
    ).with_result_backend(result_backend)
    return broker


broker = create_broker()

redis_source = RedisScheduleSource(
    f"redis://{settings.redis.host}:{settings.redis.port}/"
)

scheduler = TaskiqScheduler(
    broker=broker,
    sources=[redis_source, LabelScheduleSource(broker)],
)

init(broker, "src.main:app")

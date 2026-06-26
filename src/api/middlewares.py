import time
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import structlog

from src.core.context import request_id_var, client_ip_var


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Middleware для добавления request_id и логирования запросов"""

    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.logger = structlog.get_logger()

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Генерация и установка request_id
        request_id = str(uuid.uuid4())
        request_id_var.set(request_id)

        client_ip = request.client.host if request.client else "unknown"
        client_ip_var.set(client_ip)

        request_path = request.url.path
        if request.query_params:
            request_path += f"?{request.query_params}"

        # Добавление контекста в structlog
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request_path,
            client_ip=client_ip,
        )

        # Логирование входящего запроса
        start_time = time.time()
        self.logger.info(
            "request_started",
            method=request.method,
            path=request.url.path,
            query_params=str(request.query_params),
            client_ip=client_ip,
        )

        try:
            # Обработка запроса
            response = await call_next(request)

            # Расчет времени выполнения
            duration_ms = (time.time() - start_time) * 1000

            # Логирование ответа
            self.logger.info(
                "request_completed",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=round(duration_ms, 2),
            )

            # Добавление request_id в заголовки ответа
            response.headers["X-Request-ID"] = request_id

            return response

        except Exception as exc:
            # Логирование необработанных исключений
            duration_ms = (time.time() - start_time) * 1000
            self.logger.critical(
                "unhandled_exception",
                method=request.method,
                path=request.url.path,
                duration_ms=round(duration_ms, 2),
                error_type=type(exc).__name__,
                error_message=str(exc),
                exc_info=True,
            )
            raise

        finally:
            structlog.contextvars.clear_contextvars()

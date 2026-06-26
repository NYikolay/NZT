from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi import Request

from starlette.exceptions import HTTPException as StarletteHTTPException

from src.core.logging_config import logger
from src.domain.exceptions import BaseAppError


def build_error_response(exc: BaseAppError, error_id: str | None = None) -> dict:
    """Формирует тело ответа из любого BaseAppError"""
    body = {
        "error": True,
        "code": exc.error_code or "UNKNOWN_ERROR",
        "message": exc.description or exc.message or "Произошла ошибка",
    }
    if exc.details:
        body["details"] = exc.details
    if error_id:
        body["error_id"] = error_id
    return body


async def app_error_handler(request: Request, exc: BaseAppError):
    """Все доменные и инфраструктурные ошибки"""

    # Определение уровня логирования
    log_level = "warning"

    # Логирование с соответствующим уровнем
    log_method = getattr(logger, log_level)
    log_method(
        exc.error_code,
        error_id=exc.error_id,
        message=exc.message,
        description=exc.description,
        path=request.url.path,
        method=request.method,
        details=exc.details,
        status_code=exc.status_code,
    )

    status_code = exc.status_code or 400
    return JSONResponse(
        status_code=status_code,
        content=build_error_response(exc),
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Ошибки валидации Pydantic"""
    details = []
    for error in exc.errors():
        field = " → ".join(str(loc) for loc in error["loc"])
        details.append(
            {
                "field": field,
                "message": error["msg"],
                "type": error["type"],
            }
        )

    app_error = ValidationError(details=details)
    return await app_error_handler(request, app_error)


async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Стандартные HTTP-ошибки Starlette (404, 405)"""

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "code": "HTTP_ERROR",
            "message": exc.detail,
        },
    )


async def unhandled_exception_handler(request: Request, exc: Exception):
    """Последний рубеж — необработанные исключения"""
    logger.critical(
        "unhandled_exception",
        error_type=type(exc).__name__,
        error_message=str(exc),
        path=request.url.path,
        method=request.method,
        exc_info=True,
    )

    app_error = InternalError()
    return JSONResponse(
        status_code=500,
        content=build_error_response(app_error),
    )


class AccessDeniedError(BaseAppError):
    """Нет прав на действие"""

    def __init__(self, message: str = "Недостаточно прав"):
        super().__init__(
            message=message,
            description="У вас нет прав для выполнения этого действия",
            error_code="ACCESS_DENIED",
            status_code=403,
        )


class AccountLockedError(BaseAppError):
    """Аккаунт заблокирован"""

    def __init__(self, reason: str | None = None, unlocked_at: str | None = None):
        super().__init__(
            message=f"Аккаунт заблокирован: {reason or 'не указана'}",
            description="Ваш аккаунт заблокирован",
            error_code="ACCOUNT_LOCKED",
            status_code=423,
            details={"unlocked_at": unlocked_at},
        )


class RateLimitExceededError(BaseAppError):
    """Превышен лимит запросов"""

    def __init__(self, retry_after: int | None = None):
        super().__init__(
            message="Превышен лимит запросов",
            description="Слишком много запросов. Попробуйте позже",
            error_code="RATE_LIMIT_EXCEEDED",
            status_code=429,
            details={"retry_after": retry_after},
        )


class UpstreamServiceError(BaseAppError):
    """Ошибка внешнего сервиса"""

    def __init__(self, service: str, detail: str | None = None):
        super().__init__(
            message=f"Сервис '{service}' недоступен: {detail or 'неизвестная ошибка'}",
            description="Сервис временно недоступен. Попробуйте позже",
            error_code="UPSTREAM_SERVICE_ERROR",
            status_code=502,
            details={"service": service},
        )


class UpstreamTimeoutError(BaseAppError):
    """Таймаут внешнего сервиса"""

    def __init__(self, service: str):
        super().__init__(
            message=f"Таймаут запроса к сервису '{service}'",
            description="Сервис не отвечает. Попробуйте позже",
            error_code="UPSTREAM_TIMEOUT",
            status_code=504,
            details={"service": service},
        )


class ValidationError(BaseAppError):
    """Ошибка валидации входных данных"""

    def __init__(self, details: list | None = None):
        super().__init__(
            message="Ошибка валидации данных",
            description="Переданы некорректные данные",
            error_code="VALIDATION_ERROR",
            status_code=422,
            details=details or [],
        )


class AuthenticationError(BaseAppError):
    """Не авторизован"""

    def __init__(self, message: str = "Не авторизован"):
        super().__init__(
            message=message,
            description="Для выполнения запроса необходима авторизация",
            error_code="UNAUTHORIZED",
            status_code=401,
        )


class InternalError(BaseAppError):
    """Внутренняя ошибка сервера (500)"""

    def __init__(self, error_id: str | None = None):
        super().__init__(
            message=f"Внутренняя ошибка сервера [error_id={error_id}]",
            description="Произошла внутренняя ошибка. Мы уже работаем над её исправлением",
            error_code="INTERNAL_ERROR",
            status_code=500,
            details={"error_id": error_id},
        )

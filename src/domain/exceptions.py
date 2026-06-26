import uuid
from typing import Any


class BaseAppError(Exception):
    """Базовое исключение приложения.

    Attributes:
        message: короткое сообщение для разработчика (логи, отладка)
        description: человекочитаемое описание для пользователя
        error_code: машиночитаемый код ошибки
        status_code: HTTP-статус (опционально, для транспорта)
        details: дополнительные данные (поля с ошибками, id сущностей)
        error_id: уникальный идентификатор ошибки (генерируется автоматически)
    """

    def __init__(
        self,
        *,
        message: str | None = None,
        description: str | None = None,
        error_code: str | None = None,
        status_code: int | None = None,
        details: dict[str, Any] | list | None = None,
        error_id: str | None = None,
    ):
        self.message = message
        self.description = description
        self.error_code = error_code
        self.status_code = status_code
        self.details = details
        self.error_id = error_id or uuid.uuid4().hex[:12]
        super().__init__(self.message)


class EntityNotFoundError(BaseAppError):
    """Сущность не найдена"""

    def __init__(self, entity: str, entity_id: Any):
        super().__init__(
            message=f"{entity} с id={entity_id} не найден",
            description=f"{entity} не найден",
            error_code=f"{entity.upper()}_NOT_FOUND",
            status_code=404,
            details={"entity": entity, "id": str(entity_id)},
        )


class DuplicateEntityError(BaseAppError):
    """Нарушение уникальности"""

    def __init__(self, entity: str, field: str, value: str):
        super().__init__(
            message=f"{entity} с {field}={value} уже существует",
            description=f"{entity} с таким {field} уже существует",
            error_code=f"{entity.upper()}_ALREADY_EXISTS",
            status_code=409,
            details={"entity": entity, "field": field},
        )


class InvalidStateError(BaseAppError):
    """Нарушение бизнес-правила — действие невозможно в текущем состоянии"""

    def __init__(self, message: str, error_code: str | None = None):
        super().__init__(
            message=message,
            description=message,
            error_code=error_code or "INVALID_STATE",
            status_code=409,
        )

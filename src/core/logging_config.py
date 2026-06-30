import logging
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from pathlib import Path

import structlog
from structlog.types import Processor

from src.core.config import settings
from src.core.context import request_id_var, user_id_var


def mask_sensitive_data(logger, method_name, event_dict):
    """
    Structlog shared processor.
    Mask sensitive data in logs, such as password, tokens, secret keys
    """

    sensitive_keys = {"password", "token", "secret", "api_key"}
    sensitive_patterns = ["authorization", "bearer", "x-api-key"]

    def mask_value(value, key=""):
        if any(sk in key.lower() for sk in sensitive_keys):
            return "***MASKED***"
        if isinstance(value, str):
            for pattern in sensitive_patterns:
                if pattern in value.lower():
                    return "***MASKED***"
        return value

    # Mask sensetive data in structlog event_dict
    masked_dict = {}

    for key, value in event_dict.items():
        if isinstance(value, dict):
            masked_dict[key] = {k: mask_value(v, k) for k, v in value.items()}
        else:
            masked_dict[key] = mask_value(value, key)

    return masked_dict


def add_request_context(logger, method_name, event_dict):
    """
    Structlog shared processor.
    Adding variables from contextvars
    """

    rid = request_id_var.get()
    if rid:
        event_dict["request_id"] = rid

    uid = user_id_var.get()
    if uid:
        event_dict["user_id"] = uid

    return event_dict


def add_service_context(logger, method_name, event_dict):
    """
    Structlog shared processor.
    Adding service metadata for Loki labeling
    """
    event_dict["service"] = "nzt-backend"
    event_dict["environment"] = settings.ENVIRONMENT
    return event_dict


def configure_logging() -> structlog.BoundLogger:
    """
    Set logging depends on local variables
    """

    log_level = settings.LOG_LEVEL.upper()
    log_format = settings.LOG_FORMAT
    log_file = settings.LOG_FILE
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level))
    root_logger.handlers.clear()

    # Базовые процессоры
    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        add_request_context,
        add_service_context,
        mask_sensitive_data,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    if log_format == "json":
        structlog.configure(
            processors=shared_processors
            + [
                structlog.processors.dict_tracebacks,
                structlog.processors.JSONRenderer(),
            ],
            wrapper_class=structlog.stdlib.BoundLogger,
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )
    else:
        structlog.configure(
            processors=shared_processors + [structlog.dev.ConsoleRenderer(colors=True)],
            wrapper_class=structlog.stdlib.BoundLogger,
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )

    if "DAILY" in settings.LOG_ROTATION:
        file_handler = TimedRotatingFileHandler(
            log_file, when="midnight", interval=1, backupCount=30
        )
    else:
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5,
        )

    file_handler.setLevel(getattr(logging, log_level))
    formatter = logging.Formatter("%(message)s")
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    return structlog.get_logger()


logger = configure_logging()

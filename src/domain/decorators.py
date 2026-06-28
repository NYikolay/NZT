import functools
import time
from typing import Callable, Any
import inspect

import structlog

from src.domain.exceptions import BaseAppError

logger = structlog.get_logger()


def log_domain_operation(operation_name: str | None = None) -> Callable:
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            op_name = operation_name or func.__name__
            start_time = time.time()

            logger.debug(
                "domain_operation_started",
                operation=op_name,
                args_count=len(args),
                kwargs_keys=list(kwargs.keys()),
            )

            try:
                result = await func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000

                logger.debug(
                    "domain_operation_completed",
                    operation=op_name,
                    duration_ms=round(duration_ms, 2),
                )
                return result
            except BaseAppError as e:
                logger.warning(
                    "domain_operation_failed",
                    operation=op_name,
                    error_code=e.error_code,
                    message=e.message,
                )
                raise
            except Exception as e:
                logger.error(
                    "domain_operation_error",
                    operation=op_name,
                    error_type=type(e).__name__,
                    error_message=str(e),
                    exc_info=True,
                )
                raise

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            op_name = operation_name or func.__name__
            start_time = time.time()

            logger.debug(
                "domain_operation_started",
                operation=op_name,
            )

            try:
                result = func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000

                logger.debug(
                    "domain_operation_completed",
                    operation=op_name,
                    duration_ms=round(duration_ms, 2),
                )
                return result

            except BaseAppError as e:
                logger.warning(
                    "domain_operation_failed",
                    operation=op_name,
                    error_code=e.error_code,
                    error_id=e.error_id,
                )
                raise

            except Exception as e:
                logger.error(
                    "domain_operation_error",
                    operation=op_name,
                    error_type=type(e).__name__,
                    exc_info=True,
                )
                raise

        if inspect.iscoroutinefunction(func):
            return async_wrapper

        return sync_wrapper

    return decorator

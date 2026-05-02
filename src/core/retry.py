"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/core/retry.py
Robust retry decorator with exponential backoff and jitter.
Author : triqbit
License: MIT
"""

import functools
import logging
import random
import time
from typing import Any, Callable, Tuple, Type, Union

logger = logging.getLogger(__name__)


def with_retry(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    exceptions: Union[Type[Exception], Tuple[Type[Exception], ...]] = Exception,
    jitter: bool = True,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Decorator for retrying a function with exponential backoff and optional jitter.

    Args:
        max_retries: Maximum number of retry attempts.
        base_delay: Initial delay between retries in seconds.
        max_delay: Maximum delay between retries in seconds.
        exceptions: Exception type(s) that should trigger a retry.
        jitter: Whether to add random jitter to the delay.
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            retries = 0
            while True:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    retries += 1
                    if retries > max_retries:
                        logger.error(
                            "Max retries (%d) exceeded for %s: %s",
                            max_retries,
                            func.__name__,
                            e,
                        )
                        raise

                    delay = min(base_delay * (2 ** (retries - 1)), max_delay)
                    if jitter:
                        delay *= 0.5 + random.random()

                    logger.warning(
                        "Retry %d/%d for %s after %.2fs due to: %s",
                        retries,
                        max_retries,
                        func.__name__,
                        delay,
                        e,
                    )
                    time.sleep(delay)

        return wrapper

    return decorator

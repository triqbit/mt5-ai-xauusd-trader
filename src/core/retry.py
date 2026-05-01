"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/core/retry.py
Robust retry decorator with exponential backoff for enterprise resilience.
Author : triqbit
License: MIT
"""

import functools
import logging
import time
from typing import Any, Callable, Tuple, Type, Union

logger = logging.getLogger(__name__)


def with_retry(
    exceptions: Union[Type[Exception], Tuple[Type[Exception], ...]] = Exception,
    max_retries: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    jitter: bool = True,
):
    """
    Decorator that retries a function with exponential backoff.

    Args:
        exceptions: Exception or tuple of exceptions to catch and retry.
        max_retries: Maximum number of retry attempts.
        initial_delay: Delay before the first retry in seconds.
        backoff_factor: Factor by which the delay increases after each attempt.
        jitter: Whether to add random jitter to the delay.
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            delay = initial_delay
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt >= max_retries:
                        logger.error(
                            "Max retries (%d) reached for %s. Last error: %s",
                            max_retries,
                            func.__name__,
                            e,
                        )
                        raise

                    wait_time = delay
                    if jitter:
                        import random

                        wait_time *= 0.5 + random.random()

                    logger.warning(
                        "Retry attempt %d/%d for %s failed: %s. Retrying in %.2fs...",
                        attempt + 1,
                        max_retries,
                        func.__name__,
                        e,
                        wait_time,
                    )

                    time.sleep(wait_time)
                    delay *= backoff_factor

            # Should not be reached due to raise in loop
            if last_exception:
                raise last_exception

        return wrapper

    return decorator

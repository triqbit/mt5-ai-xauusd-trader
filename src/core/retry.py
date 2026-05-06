"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/core/retry.py
Robust retry logic with exponential backoff and jitter for transient failures.
"""

import functools
import logging
import random
import time
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)


def with_retry(
    exceptions: type[Exception] | tuple[type[Exception], ...],
    max_retries: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    jitter: bool = True,
):
    """
    Decorator for retrying a function with exponential backoff.

    Args:
        exceptions: The exception(s) to catch and retry on.
        max_retries: Maximum number of retry attempts.
        initial_delay: Initial delay between retries in seconds.
        backoff_factor: Multiplier for the delay after each retry.
        jitter: Whether to add random jitter to the delay.
    """

    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            delay = initial_delay

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    # Check if the exception is marked as non-retriable
                    if hasattr(e, "is_retriable") and not e.is_retriable:
                        logger.warning(
                            "Caught non-retriable exception %s in %s. Failing immediately.",
                            type(e).__name__,
                            func.__name__,
                        )
                        raise

                    if attempt == max_retries:
                        logger.error(
                            "Max retries (%d) reached for %s. Last error: %s",
                            max_retries,
                            func.__name__,
                            e,
                        )
                        raise

                    current_delay = delay
                    if jitter:
                        current_delay *= 0.5 + random.random()

                    logger.warning(
                        "Attempt %d/%d failed for %s: %s. Retrying in %.2fs...",
                        attempt + 1,
                        max_retries,
                        func.__name__,
                        e,
                        current_delay,
                    )
                    time.sleep(current_delay)
                    delay *= backoff_factor

        return wrapper

    return decorator

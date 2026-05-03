"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/core/retry.py
Robust retry logic with exponential backoff for enterprise resilience.
Author : triqbit
License: MIT
"""

import time
import random
import logging
import functools
from typing import Any, Callable, Optional, Tuple, Type, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")

def with_retry(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator for retrying a function with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts.
        base_delay: Initial delay between retries in seconds.
        max_delay: Maximum delay between retries in seconds.
        exponential_base: Base for exponential backoff calculation.
        jitter: Whether to add random jitter to the delay.
        exceptions: Tuple of exception types to catch and retry.
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception: Optional[Exception] = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt == max_retries:
                        logger.error(
                            "Max retries (%d) reached for %s. Final error: %s",
                            max_retries, func.__name__, e
                        )
                        raise

                    delay = min(max_delay, base_delay * (exponential_base ** attempt))
                    if jitter:
                        delay = delay * (0.5 + random.random())

                    logger.warning(
                        "Attempt %d/%d failed for %s: %s. Retrying in %.2fs...",
                        attempt + 1, max_retries + 1, func.__name__, e, delay
                    )
                    time.sleep(delay)

            # This part should theoretically not be reached due to 'raise' above
            if last_exception:
                raise last_exception
            raise RuntimeError("Unexpected state in with_retry")

        return wrapper
    return decorator

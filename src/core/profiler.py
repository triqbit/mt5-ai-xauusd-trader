"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/core/profiler.py
High-resolution performance profiling utility using context managers.
Author : triqbit
License: MIT
"""
from __future__ import annotations

import time
from contextlib import contextmanager
from typing import Any, Generator, Optional

import structlog

logger = structlog.get_logger(__name__)


class Profiler:
    """
    Context manager for measuring execution time of code blocks.
    Outputs structured logs with timing data.
    """

    def __init__(self, name: str, **context: Any) -> None:
        self.name = name
        self.context = context
        self.start_time: Optional[float] = None

    def __enter__(self) -> Profiler:
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self.start_time is None:
            return

        duration = time.perf_counter() - self.start_time
        duration_ms = duration * 1000

        log_data = {
            "event": "profile",
            "block": self.name,
            "duration_ms": round(duration_ms, 3),
            "duration_s": round(duration, 6),
            **self.context,
        }

        if exc_type:
            log_data["exception"] = str(exc_type.__name__)
            logger.error("Profile block failed", **log_data)
        else:
            logger.info("Profile block completed", **log_data)


@contextmanager
def profile(name: str, **context: Any) -> Generator[None, None, None]:
    """Functional wrapper for Profiler context manager."""
    with Profiler(name, **context):
        yield


def log_latency(name: str, duration_s: float, **context: Any) -> None:
    """Manually log a duration if context manager is not suitable."""
    logger.info(
        "Manual latency log",
        event="profile",
        block=name,
        duration_ms=round(duration_s * 1000, 3),
        **context,
    )

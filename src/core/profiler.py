"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/core/profiler.py
High-resolution performance profiling for latency tracking.
Author : triqbit
License: MIT
"""

import time
from contextlib import contextmanager
from typing import Generator

import structlog

logger = structlog.get_logger(__name__)


@contextmanager
def profile(label: str) -> Generator[None, None, None]:
    """
    Context manager to measure execution time of a code block.
    Logs the duration in milliseconds to structlog.
    """
    start_ns = time.perf_counter_ns()
    try:
        yield
    finally:
        end_ns = time.perf_counter_ns()
        duration_ms = (end_ns - start_ns) / 1_000_000
        logger.info(
            "performance_metric",
            label=label,
            duration_ms=round(duration_ms, 3),
        )

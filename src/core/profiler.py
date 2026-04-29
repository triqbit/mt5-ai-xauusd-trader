"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/core/profiler.py
High-resolution performance profiling using structlog and nanosecond-accurate counters.
Author : triqbit
License: MIT
"""
from __future__ import annotations

import time
from contextlib import contextmanager
from typing import Generator

import structlog

logger = structlog.get_logger(__name__)


@contextmanager
def profile(label: str) -> Generator[None, None, None]:
    """
    Context manager to profile a block of code and log its duration.
    Uses time.perf_counter_ns() for nanosecond precision.
    """
    start_ns = time.perf_counter_ns()
    try:
        yield
    finally:
        end_ns = time.perf_counter_ns()
        duration_ms = (end_ns - start_ns) / 1_000_000
        logger.info(
            "profiling_event",
            label=label,
            duration_ms=round(duration_ms, 3),
            duration_ns=end_ns - start_ns,
        )

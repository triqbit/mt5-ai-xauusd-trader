"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/core/profiler.py
High-resolution profiling utilities for latency tracking.
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
    Context manager to measure and log execution time of a code block.

    Args:
        label: A descriptive name for the code block being profiled.
    """
    start_time = time.perf_counter_ns()
    try:
        yield
    finally:
        end_time = time.perf_counter_ns()
        duration_ms = (end_time - start_time) / 1_000_000
        logger.info(
            "performance_metric",
            label=label,
            duration_ms=round(duration_ms, 3),
        )


__all__ = ["profile"]

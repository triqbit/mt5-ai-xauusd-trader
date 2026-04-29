"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/core/profiler.py
High-resolution performance profiling using structlog.
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
def profile(label: str, **kwargs) -> Generator[None, None, None]:
    """
    Context manager to measure and log execution time of a code block.

    Args:
        label: Name of the section being profiled.
        **kwargs: Additional structured data to include in the log.
    """
    start_ns = time.perf_counter_ns()
    try:
        yield
    finally:
        duration_ns = time.perf_counter_ns() - start_ns
        duration_ms = duration_ns / 1_000_000
        logger.info(
            "Performance profiling",
            label=label,
            duration_ms=round(duration_ms, 3),
            **kwargs
        )

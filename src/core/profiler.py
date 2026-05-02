"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/core/profiler.py
High-resolution performance profiling utilities.
Author : triqbit
License: MIT
"""
from __future__ import annotations

import time
from contextlib import contextmanager
from typing import Generator

import structlog

try:
    from prometheus_client import Histogram

    BLOCK_LATENCY = Histogram(
        "trading_block_duration_seconds",
        "Execution time of profiled code blocks in seconds",
        ["block_label"],
    )
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False

logger = structlog.get_logger(__name__)


@contextmanager
def profile(label: str) -> Generator[None, None, None]:
    """
    Context manager to measure and log execution duration of a code block.

    Args:
        label: Descriptive name for the block being profiled.
    """
    start_time = time.perf_counter()
    try:
        yield
    finally:
        duration = time.perf_counter() - start_time
        duration_ms = round(duration * 1000, 3)

        if PROMETHEUS_AVAILABLE:
            BLOCK_LATENCY.labels(block_label=label).observe(duration)

        logger.info("performance_metric", label=label, duration_ms=duration_ms)

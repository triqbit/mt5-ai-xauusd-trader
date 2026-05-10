"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/core/profiler.py
High-resolution performance profiling utilities.
Author : triqbit
License: MIT
"""

from __future__ import annotations

import time
from collections.abc import Generator
from contextlib import contextmanager

import structlog

# Conditional import to avoid circular dependencies and handle missing metrics
try:
    from src.core.monitor import TRADING_BLOCK_DURATION
except ImportError:
    TRADING_BLOCK_DURATION = None

logger = structlog.get_logger(__name__)


@contextmanager
def profile(label: str, slow_threshold_ms: float | None = None) -> Generator[None, None, None]:
    """
    Context manager to measure and log execution duration of a code block.

    Args:
        label: Descriptive name for the block being profiled.
        slow_threshold_ms: If provided, logs at INFO level only if duration exceeds this threshold.
                          Otherwise, logs at DEBUG level.
    """
    start_time = time.perf_counter()
    try:
        yield
    finally:
        duration = time.perf_counter() - start_time
        duration_ms = round(duration * 1000, 3)

        # Determine log level: INFO for slow blocks, DEBUG for normal ones
        if slow_threshold_ms is not None and duration_ms >= slow_threshold_ms:
            logger.info(
                "performance_metric_slow",
                label=label,
                duration_ms=duration_ms,
                threshold_ms=slow_threshold_ms,
            )
        else:
            logger.debug("performance_metric", label=label, duration_ms=duration_ms)

        # Log to Prometheus Histogram if available
        if TRADING_BLOCK_DURATION is not None:
            try:
                TRADING_BLOCK_DURATION.labels(block_label=label).observe(duration)
            except Exception as e:
                # Avoid crashing the trading loop if metrics fail
                logger.debug("Failed to log Prometheus metric", error=str(e))

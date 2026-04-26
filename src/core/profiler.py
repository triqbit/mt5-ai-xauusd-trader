"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/core/profiler.py
Performance profiling and real-time metrics collection.
Author : triqbit
License: MIT
"""
from __future__ import annotations

import functools
import logging
import time
from contextlib import contextmanager
from typing import Any, Callable, Dict, Optional, TypeVar

import psutil
from prometheus_client import Counter, Gauge, Histogram, start_http_server

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])

# ── Prometheus Metrics ──────────────────────────────────────────────────────

# Latency Histograms
LATENCY = Histogram(
    "trading_latency_seconds",
    "Latency of various operations in seconds",
    ["operation", "component"],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0),
)

# Model Inference Latency
MODEL_INFERENCE_LATENCY = Histogram(
    "model_inference_seconds",
    "Model inference time in seconds",
    ["model_name"],
)

# Feature Engineering Latency
FEATURE_ENGINEERING_LATENCY = Histogram(
    "feature_engineering_seconds",
    "Feature engineering time per timeframe",
    ["timeframe"],
)

# Signal Generation Latency (End-to-End)
SIGNAL_GENERATION_LATENCY = Histogram(
    "signal_generation_seconds",
    "End-to-end signal generation latency",
)

# DB Query Performance
DB_QUERY_LATENCY = Histogram(
    "db_query_seconds",
    "Database query execution time",
    ["query_type"],
)

# API Call Response Times
API_CALL_LATENCY = Histogram(
    "api_call_seconds",
    "External API call response times",
    ["api_name", "endpoint"],
)

# Memory Usage Trends
MEMORY_USAGE_BYTES = Gauge(
    "process_memory_usage_bytes",
    "Current memory usage of the process in bytes",
    ["type"],
)

# Error Counter
ERRORS = Counter(
    "trading_errors_total",
    "Total number of errors encountered",
    ["component", "error_type"],
)

# ── Profiler Utilities ──────────────────────────────────────────────────────

def profile_latency(operation: str, component: str) -> Callable[[F], F]:
    """Decorator to profile function latency."""
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = time.perf_counter() - start_time
                LATENCY.labels(operation=operation, component=component).observe(duration)
        return wrapper  # type: ignore
    return decorator

@contextmanager
def track_latency(operation: str, component: str):
    """Context manager to track latency."""
    start_time = time.perf_counter()
    try:
        yield
    finally:
        duration = time.perf_counter() - start_time
        LATENCY.labels(operation=operation, component=component).observe(duration)

def track_model_inference(model_name: str) -> Callable[[F], F]:
    """Decorator for model inference timing."""
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.perf_counter()
            try:
                return func(*args, **kwargs)
            finally:
                duration = time.perf_counter() - start_time
                MODEL_INFERENCE_LATENCY.labels(model_name=model_name).observe(duration)
        return wrapper  # type: ignore
    return decorator

def update_memory_metrics() -> None:
    """Update memory usage gauges."""
    process = psutil.Process()
    mem_info = process.memory_info()
    MEMORY_USAGE_BYTES.labels(type="rss").set(mem_info.rss)
    MEMORY_USAGE_BYTES.labels(type="vms").set(mem_info.vms)

def start_metrics_server(port: int = 8000) -> None:
    """Start the Prometheus HTTP server."""
    try:
        start_http_server(port)
        logger.info("Prometheus metrics server started on port %d", port)
    except Exception as e:
        logger.error("Failed to start Prometheus server: %s", e)

class Profiler:
    """Centralized profiling interface."""

    @staticmethod
    def start(port: int = 8000) -> None:
        start_metrics_server(port)

    @staticmethod
    def update_system_metrics() -> None:
        update_memory_metrics()

__all__ = [
    "LATENCY",
    "MODEL_INFERENCE_LATENCY",
    "FEATURE_ENGINEERING_LATENCY",
    "SIGNAL_GENERATION_LATENCY",
    "DB_QUERY_LATENCY",
    "API_CALL_LATENCY",
    "MEMORY_USAGE_BYTES",
    "ERRORS",
    "profile_latency",
    "track_latency",
    "track_model_inference",
    "Profiler",
]

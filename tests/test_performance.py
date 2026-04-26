"""
MT5 AI/ML Trading Bot - Enterprise Edition
tests/test_performance.py
Performance regression tests for the trading bot.
"""
import time
import pytest
from prometheus_client import REGISTRY
from src.core.profiler import (
    FEATURE_ENGINEERING_LATENCY,
    SIGNAL_GENERATION_LATENCY,
    MODEL_INFERENCE_LATENCY,
    DB_QUERY_LATENCY,
    API_CALL_LATENCY,
    MEMORY_USAGE_BYTES,
    Profiler
)

def get_metric_value(metric_name, labels=None):
    """Helper to get metric value from REGISTRY."""
    for metric in REGISTRY.collect():
        # Prometheus client might add _count, _sum, _bucket suffixes
        if metric.name == metric_name or metric.name == metric_name.replace("_count", "") or metric.name == metric_name.replace("_sum", ""):
            for sample in metric.samples:
                if sample.name == metric_name:
                    if labels:
                        if all(sample.labels.get(k) == v for k, v in labels.items()):
                            return sample.value
                    else:
                        return sample.value
    return 0.0

def test_feature_engineering_latency_tracking():
    """Verify that feature engineering latency is tracked."""
    with FEATURE_ENGINEERING_LATENCY.labels(timeframe="M5").time():
        time.sleep(0.01)

    val = get_metric_value("feature_engineering_seconds_count", {"timeframe": "M5"})
    assert val >= 1

    total_time = get_metric_value("feature_engineering_seconds_sum", {"timeframe": "M5"})
    assert total_time >= 0.01

def test_model_inference_latency_tracking():
    """Verify that model inference latency is tracked."""
    with MODEL_INFERENCE_LATENCY.labels(model_name="test_model").time():
        time.sleep(0.02)

    val = get_metric_value("model_inference_seconds_count", {"model_name": "test_model"})
    assert val >= 1

    total_time = get_metric_value("model_inference_seconds_sum", {"model_name": "test_model"})
    assert total_time >= 0.02

def test_signal_generation_latency_tracking():
    """Verify that signal generation latency is tracked."""
    with SIGNAL_GENERATION_LATENCY.time():
        time.sleep(0.03)

    val = get_metric_value("signal_generation_seconds_count")
    assert val >= 1

    total_time = get_metric_value("signal_generation_seconds_sum")
    assert total_time >= 0.03

def test_db_query_latency_tracking():
    """Verify that DB query latency is tracked."""
    with DB_QUERY_LATENCY.labels(query_type="test_query").time():
        time.sleep(0.005)

    val = get_metric_value("db_query_seconds_count", {"query_type": "test_query"})
    assert val >= 1

def test_api_call_latency_tracking():
    """Verify that API call latency is tracked."""
    with API_CALL_LATENCY.labels(api_name="TestAPI", endpoint="test_endpoint").time():
        time.sleep(0.01)

    val = get_metric_value("api_call_seconds_count", {"api_name": "TestAPI", "endpoint": "test_endpoint"})
    assert val >= 1

def test_memory_usage_tracking():
    """Verify that memory usage is tracked."""
    Profiler.update_system_metrics()

    rss = get_metric_value("process_memory_usage_bytes", {"type": "rss"})
    vms = get_metric_value("process_memory_usage_bytes", {"type": "vms"})

    assert rss > 0
    assert vms > 0

@pytest.mark.performance
def test_latency_thresholds():
    """Regression test for latency thresholds."""
    # Example thresholds
    MAX_SIGNAL_GEN_TIME = 0.5 # 500ms

    start = time.perf_counter()
    # Simulate signal generation
    time.sleep(0.1)
    end = time.perf_counter()

    duration = end - start
    assert duration < MAX_SIGNAL_GEN_TIME, f"Signal generation too slow: {duration}s > {MAX_SIGNAL_GEN_TIME}s"

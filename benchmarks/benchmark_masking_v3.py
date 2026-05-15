
import time
import structlog
import logging
import sys
from src.core.log_config import SecretMaskingProcessor
from pydantic import SecretStr

def benchmark_masking_overhead(n=100000):
    processor = SecretMaskingProcessor()
    processor.secrets = {"secret-1", "secret-2", "secret-3", "secret-4"}

    # Mixed dictionary: some primitives, some nested
    event = {
        "event": "performance_metric",
        "label": "bt_observation_normalization",
        "duration_ms": 0.045,
        "trace_id": "uuid-123-456",
        "is_approved": True,
        "nested": {"key": 123, "status": "OK"},
        "tags": ["perf", "backtest"]
    }

    print(f"Benchmarking redact_any with {len(processor.secrets)} secrets, {n} iterations...")

    # Measure total time for a large number of calls
    start = time.perf_counter()
    for _ in range(n):
        e = event.copy()
        _ = processor.redact_any(e, _in_place=True)
    end = time.perf_counter()

    avg_time = (end - start) / n * 1e6
    print(f"Average in-place time: {avg_time:.2f}us")

    # Specifically measure primitives vs strings
    start = time.perf_counter()
    for _ in range(n):
        _ = processor.redact_any(123.45)
    end = time.perf_counter()
    print(f"Average float redact time: {(end-start)/n*1e6:.2f}us")

    start = time.perf_counter()
    for _ in range(n):
        _ = processor.redact_any("short")
    end = time.perf_counter()
    print(f"Average short string redact time: {(end-start)/n*1e6:.2f}us")

if __name__ == "__main__":
    benchmark_masking_overhead()

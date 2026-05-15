
import time
import structlog
import logging
import sys
from src.core.log_config import SecretMaskingProcessor
from pydantic import SecretStr

def benchmark_masking_overhead(n=10000):
    # Setup a realistic config with some secrets
    class MockConfig:
        def __init__(self):
            self.mt5_password = SecretStr("very-secret-password-12345")
            self.telegram_token = SecretStr("123456789:ABCdefGHIjklMNOpqrSTUvwxYZ")
            self.database_url = SecretStr("postgresql://user:password-with-at-@-host:5432/db")
            self.metaapi_token = SecretStr("meta-api-long-token-value-here")

        @property
        def model_fields(self):
            return ["mt5_password", "telegram_token", "database_url", "metaapi_token"]

    mock_cfg = MockConfig()
    processor = SecretMaskingProcessor()
    # Manually populate secrets to simulate update_secrets behavior
    processor.secrets = {"very-secret-password-12345", "123456789:ABCdefGHIjklMNOpqrSTUvwxYZ", "password-with-at-", "meta-api-long-token-value-here"}

    event = {"event": "performance_metric", "label": "bt_observation_normalization", "duration_ms": 0.045, "trace_id": "uuid-123-456"}

    print(f"Benchmarking redact_any with {len(processor.secrets)} secrets, {n} iterations...")

    # OLD behavior simulated by passing _in_place=False (default)
    start = time.perf_counter()
    for _ in range(n):
        _ = processor.redact_any(event.copy(), _in_place=False)
    end = time.perf_counter()
    old_time = end - start
    print(f"Copying (Old): {old_time:.4f}s ({old_time/n*1e6:.2f}us/call)")

    # NEW behavior: in-place
    start = time.perf_counter()
    for _ in range(n):
        e = event.copy()
        _ = processor.redact_any(e, _in_place=True)
    end = time.perf_counter()
    new_time = end - start
    print(f"In-place (New): {new_time:.4f}s ({new_time/n*1e6:.2f}us/call)")

    print(f"Improvement: {(old_time - new_time) / old_time:.1%}")

if __name__ == "__main__":
    benchmark_masking_overhead(100000)

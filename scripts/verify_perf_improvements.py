import time
from unittest.mock import MagicMock, patch
import pandas as pd
import numpy as np
from main import run_live
from src.core.profiler import BLOCK_LATENCY

def test_prometheus_integration():
    # Setup mocks
    cfg = MagicMock()
    cfg.symbol = "XAUUSD"
    cfg.mode = "demo"
    cfg.timeframe = "M5"
    cfg.algorithm = "ensemble"

    connector = MagicMock()
    # Mock OHLCV data
    dates = pd.date_range(start="2024-01-01", periods=200, freq="5min")
    df = pd.DataFrame({
        "open": [2000.0] * 200,
        "high": [2100.0] * 200,
        "low": [1900.0] * 200,
        "close": [2050.0] * 200,
        "tick_volume": [500] * 200
    }, index=dates)
    connector.get_ohlcv.return_value = df
    connector.get_tick.return_value = {"bid": 2049.0, "ask": 2051.0}
    connector.get_positions.return_value = []
    connector.get_account_balance.return_value = 10000.0

    risk = MagicMock()
    risk.open_positions = {}

    model = MagicMock()
    model.predict.return_value = (0, 0.8, {}) # HOLD

    monitor = MagicMock()

    # We only want to run one iteration for testing
    with patch("time.sleep", side_effect=KeyboardInterrupt):
        try:
            run_live(cfg, connector, risk, model, monitor=monitor)
        except KeyboardInterrupt:
            pass

    # Check if profiler recorded loop_total
    # Since we use prometheus_client, we can check the metrics
    found = False
    for metric in BLOCK_LATENCY.collect():
        for sample in metric.samples:
            if sample.labels["block_label"] == "loop_total":
                found = True
                print(f"Verified: loop_total metric found with value {sample.value}")

    if not found:
        raise AssertionError("Metric 'loop_total' not found in Prometheus histogram")

if __name__ == "__main__":
    try:
        test_prometheus_integration()
        print("Verification SUCCESS")
    except Exception as e:
        print(f"Verification FAILED: {e}")
        exit(1)

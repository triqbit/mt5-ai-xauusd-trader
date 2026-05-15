
import pandas as pd
import numpy as np
from src.trading.backtester import BacktestEngine
from src.core.feature_engineering import FeatureEngineer
from src.trading.execution_filter import ExecutionFilter
import time
import structlog
import logging

# Configure logging to see profiling if desired, or keep it quiet
structlog.configure(
    processors=[structlog.processors.JSONRenderer()],
    logger_factory=structlog.stdlib.LoggerFactory(),
)
logging.getLogger().setLevel(logging.INFO)

class MockModel:
    def predict(self, obs, **kwargs):
        # Always return a buy signal to exercise the execution filter and trade simulation
        return type('Signal', (), {'direction': 1, 'confidence': 0.7})

def benchmark_backtest(n_bars=2000):
    print(f"Benchmarking Backtest with {n_bars} bars...")
    data = pd.DataFrame({
        "open": np.random.randn(n_bars) + 2000,
        "high": np.random.randn(n_bars) + 2002,
        "low": np.random.randn(n_bars) + 1998,
        "close": np.random.randn(n_bars) + 2000,
        "tick_volume": np.random.randint(100, 1000, n_bars)
    }, index=pd.date_range("2024-01-01", periods=n_bars, freq="5min"))

    # Use a default FeatureEngineer and ExecutionFilter
    fe = FeatureEngineer(base_timeframe="M5", timeframes=["M15", "H1"]) # Fewer timeframes for faster test
    ef = ExecutionFilter()

    engine = BacktestEngine("XAUUSD", feature_engineer=fe, execution_filter=ef)
    model = MockModel()

    start = time.perf_counter()
    report = engine.run_walk_forward(data, model, train_window=500, test_window=100, step_size=100)
    end = time.perf_counter()

    print(f"Backtest completed in {end - start:.2f}s")
    print(f"Total trades: {report.total_trades}")
    return end - start

if __name__ == "__main__":
    benchmark_backtest(2000)
    # Set log level to DEBUG to see overhead if any
    # logging.getLogger().setLevel(logging.DEBUG)
    # benchmark_backtest(2000)

import pandas as pd
import numpy as np
from src.core.config import get_config
from src.core.feature_engineering import FeatureEngineer
from src.models.ensemble import EnsembleModel
from src.trading.backtester import BacktestEngine

def test_backtest_engine():
    # Force confidence threshold to 0 for dummy testing
    cfg = get_config()
    cfg.confidence_threshold = 0.0

    fe = FeatureEngineer()
    model = EnsembleModel(device="cpu")

    # Mock model predict to return some signals
    def mock_predict(obs):
        return np.random.choice([1, -1, 0]), 0.8, {}

    model.predict = mock_predict

    # Create dummy data
    dates = pd.date_range(start="2023-01-01", periods=2000, freq="5min")
    data = pd.DataFrame({
        "open": np.random.randn(2000) + 2000,
        "high": np.random.randn(2000) + 2005,
        "low": np.random.randn(2000) + 1995,
        "close": np.random.randn(2000) + 2000,
        "tick_volume": np.random.randint(100, 1000, 2000)
    }, index=dates)

    # Fit FE
    fe.fit(fe.extract_features(data.head(500)))

    engine = BacktestEngine(cfg, fe, model)
    report = engine.run(data)

    assert report is not None
    assert report.total_trades > 0
    print("\nBacktest Report Test Passed")
    print(report)

if __name__ == "__main__":
    test_backtest_engine()

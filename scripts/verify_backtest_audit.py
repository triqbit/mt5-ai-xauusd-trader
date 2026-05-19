import os
import sys
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

# Ensure src is in path
sys.path.append(os.getcwd())

from src.core.audit_log import AuditLogger
from src.core.feature_engineering import FeatureEngineer
from src.trading.backtester import BacktestEngine


def create_synthetic_data(n_bars=3000):
    start_time = datetime.now()
    times = [start_time + timedelta(minutes=i * 5) for i in range(n_bars)]
    data = {
        "time": times,
        "open": np.random.uniform(2300, 2400, n_bars),
        "high": np.random.uniform(2300, 2400, n_bars),
        "low": np.random.uniform(2300, 2400, n_bars),
        "close": np.random.uniform(2300, 2400, n_bars),
        "tick_volume": np.random.randint(100, 1000, n_bars),
    }
    df = pd.DataFrame(data)
    # Ensure high is highest, low is lowest
    df["high"] = df[["open", "high", "low", "close"]].max(axis=1)
    df["low"] = df[["open", "high", "low", "close"]].min(axis=1)
    df.set_index("time", inplace=True)
    return df


class MockModel:
    def predict(self, obs):
        from src.core.schemas import TradeSignal

        # Always return a HOLD signal to keep it fast
        return TradeSignal(symbol="XAUUSD", direction=0, confidence=0.0)


def main():
    print("Initializing AuditLogger...")
    audit_db = "audit.db"
    if os.path.exists(audit_db):
        os.remove(audit_db)

    # Initialize singleton
    AuditLogger(db_url=f"sqlite:///{audit_db}")

    print("Creating synthetic data...")
    data = create_synthetic_data()

    print("Running backtest...")
    fe = FeatureEngineer(base_timeframe="M5", timeframes=["M15", "H1"])
    engine = BacktestEngine(symbol="XAUUSD", feature_engineer=fe)
    model = MockModel()

    # Run with small windows for speed
    engine.run_walk_forward(data, model, train_window=500, test_window=100, step_size=100)

    print("Backtest finished.")


if __name__ == "__main__":
    main()

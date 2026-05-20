from datetime import datetime, timedelta

import numpy as np
import pandas as pd
from sqlalchemy import text

from src.core.audit_log import AuditLogger
from src.core.feature_engineering import FeatureEngineer
from src.core.schemas import TradeSignal
from src.trading.backtester import BacktestEngine


def create_synthetic_data(n_bars=3000):
    start_time = datetime.now()
    times = [start_time + timedelta(minutes=i*5) for i in range(n_bars)]
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
        # Always return a HOLD signal
        return TradeSignal(symbol="XAUUSD", direction=0, confidence=0.0)

def test_backtest_auditing_integration(tmp_path):
    """
    Verifies that running a backtest records auditing events in the database.
    """
    audit_db_file = tmp_path / "audit.db"
    audit_db_url = f"sqlite:///{audit_db_file}"

    # Initialize AuditLogger singleton for this test
    # We must reset the singleton first if it was already initialized
    AuditLogger._instance = None
    AuditLogger._initialized = False
    logger = AuditLogger(db_url=audit_db_url)

    data = create_synthetic_data()
    fe = FeatureEngineer(base_timeframe="M5", timeframes=["M15", "H1"])
    engine = BacktestEngine(symbol="XAUUSD", feature_engineer=fe)
    model = MockModel()

    # Run backtest
    engine.run_walk_forward(data, model, train_window=500, test_window=100, step_size=100)

    # Verify audit logs
    with logger.Session() as session:
        # Check for started event
        started = session.execute(
            text("SELECT * FROM audit_log WHERE action='backtest_started'")
        ).fetchone()
        assert started is not None

        # Check for completed event
        completed = session.execute(
            text("SELECT * FROM audit_log WHERE action='backtest_completed'")
        ).fetchone()
        assert completed is not None

        # metadata_json might be returned as a string in some environments/versions
        import json
        metadata = completed.metadata_json
        if isinstance(metadata, str):
            metadata = json.loads(metadata)

        assert "duration_seconds" in metadata
        assert metadata["symbol"] == "XAUUSD"

    # Cleanup singleton to avoid side effects on other tests
    AuditLogger._instance = None
    AuditLogger._initialized = False

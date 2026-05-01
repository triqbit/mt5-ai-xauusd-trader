
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timezone
from src.core.feature_engineering import FeatureEngineer
from src.trading.execution_filter import ExecutionFilter, ExecutionDecision
from src.trading.backtester import BacktestEngine
from src.trading.risk_manager import TradeSignal

def test_feature_engineer_comprehensive():
    # Create data with enough bars for all indicators (including large EMA lookbacks)
    n_bars = 2000
    df = pd.DataFrame({
        "open": np.random.randn(n_bars) + 2300,
        "high": np.random.randn(n_bars) + 2310,
        "low": np.random.randn(n_bars) + 2290,
        "close": np.random.randn(n_bars) + 2300,
        "tick_volume": np.random.randint(100, 1000, n_bars)
    })
    df.index = pd.date_range(start="2023-01-01", periods=n_bars, freq="5min")

    fe = FeatureEngineer()
    df_features = fe.generate_features(df)

    # 1. Feature count check
    assert len(fe.get_feature_names()) >= 140

    # 2. Specific indicator presence
    expected_cols = ["rsi_14", "ema_200", "macd_12_26", "atr_14", "bb_20_2.0_up", "hour_sin"]
    for col in expected_cols:
        assert col in df_features.columns

    # 3. No NaNs in the tail (after indicators stabilized)
    assert not df_features.iloc[1000:].isnull().any().any()

    # 4. Normalization check
    df_norm = fe.normalize(df_features.iloc[1000:], method="zscore")
    assert abs(df_norm["rsi_14"].mean()) < 1e-5

    df_mm = fe.normalize(df_features.iloc[1000:], method="minmax")
    assert df_mm["rsi_14"].max() <= 1.0 + 1e-9
    assert df_mm["rsi_14"].min() >= 0.0 - 1e-9

def test_execution_filter_all_layers():
    # Create a trending scenario that SHOULD pass more layers
    n_bars = 300
    close = np.linspace(2300, 2400, n_bars) # Clear uptrend
    df = pd.DataFrame({
        "open": close - 1,
        "high": close + 2,
        "low": close - 2,
        "close": close,
        "tick_volume": [1000]*n_bars,
        "spread": [1]*n_bars
    })
    # Set time to a valid trading session (e.g. Wednesday 10:00 UTC)
    dt = datetime(2023, 1, 4, 10, 0, tzinfo=timezone.utc)
    df.index = pd.date_range(start=dt, periods=n_bars, freq="5min")

    ef = ExecutionFilter()
    signal = TradeSignal(
        symbol="XAUUSD",
        direction=1,
        entry_price=2400,
        stop_loss=2350,
        take_profit=2500,
        lot_size=0.1,
        algorithm="test",
        confidence=0.8
    )

    decision = ef.validate(signal, df, current_drawdown=0.01, timestamp=dt)
    assert isinstance(decision, ExecutionDecision)

    # Test specific layer failure: Drawdown
    decision_dd = ef.validate(signal, df, current_drawdown=0.16, timestamp=dt)
    assert decision_dd.is_approved is False

def test_backtester_walk_forward_flow():
    class ConstantModel:
        def predict(self, obs):
            return 1, 0.9, {} # Always buy

    n_bars = 3000
    df = pd.DataFrame({
        "open": np.random.randn(n_bars) + 2300,
        "high": np.random.randn(n_bars) + 2310,
        "low": np.random.randn(n_bars) + 2290,
        "close": np.random.randn(n_bars) + 2300,
        "tick_volume": np.random.randint(100, 1000, n_bars)
    })
    # Use dates that pass the session filter
    df.index = pd.date_range(start="2023-01-02 00:00", periods=n_bars, freq="5min")

    engine = BacktestEngine(initial_balance=10000.0)

    # Test single run
    report = engine.run(df.iloc[:1000], ConstantModel())
    assert isinstance(report.annualized_return, float)

    # Test walk-forward run
    wf_report = engine.run_walk_forward(df, ConstantModel(), train_bars=1000, test_bars=200)
    assert wf_report.total_trades >= 0
    assert wf_report.period_start is not None

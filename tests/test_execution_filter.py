from datetime import datetime, timezone

import numpy as np
import pandas as pd
import pytest

from src.trading.execution_filter import ExecutionFilter


@pytest.fixture
def base_df():
    """Creates a base dataframe with 300 rows of OHLCV data."""
    dates = pd.date_range(end=datetime.now(), periods=300, freq="5min")
    df = pd.DataFrame(
        {
            "open": np.linspace(1900, 2000, 300),
            "high": np.linspace(1905, 2005, 300),
            "low": np.linspace(1895, 1995, 300),
            "close": np.linspace(1900, 2000, 300),
            "tick_volume": [100] * 300,
        },
        index=dates,
    )
    return df


class TestExecutionFilter:
    def test_atr_volatility_pass(self, base_df):
        ef = ExecutionFilter()
        # Flat growth means constant small ATR
        assert ef._check_atr_volatility(base_df) is True

    def test_atr_volatility_fail(self, base_df):
        ef = ExecutionFilter()
        # Spiking the last high price to increase ATR
        df_spike = base_df.copy()
        df_spike.iloc[-1, df_spike.columns.get_loc("high")] = 3000
        df_spike.iloc[-1, df_spike.columns.get_loc("low")] = 1000
        assert ef._check_atr_volatility(df_spike) is False

    def test_trend_angle_buy_pass(self, base_df):
        ef = ExecutionFilter()
        # base_df has positive slope (1900 to 2000)
        assert ef._check_trend_angle(base_df, 1) is True

    def test_trend_angle_buy_fail(self, base_df):
        ef = ExecutionFilter()
        # Reversed slope
        df_rev = base_df.copy()
        df_rev["close"] = np.linspace(2000, 1900, 300)
        assert ef._check_trend_angle(df_rev, 1) is False

    def test_ema_sequence_buy_pass(self, base_df):
        ef = ExecutionFilter()
        # In a steady uptrend, fast > med > slow usually holds
        # 20, 50, 200 periods
        # With np.linspace(1900, 2000), EMA will be f > m > s
        assert ef._check_ema_sequence(base_df, 1) is True

    def test_ema_sequence_sell_pass(self, base_df):
        ef = ExecutionFilter()
        df_down = base_df.copy()
        df_down["close"] = np.linspace(2000, 1900, 300)
        assert ef._check_ema_sequence(df_down, -1) is True

    def test_momentum_buy_pass(self, base_df):
        ef = ExecutionFilter()
        # Steady uptrend means RSI > 50
        assert ef._check_momentum(base_df, 1) is True

    def test_momentum_sell_pass(self, base_df):
        ef = ExecutionFilter()
        df_down = base_df.copy()
        df_down["close"] = np.linspace(2000, 1900, 300)
        assert ef._check_momentum(df_down, -1) is True

    def test_session_pass(self):
        ef = ExecutionFilter()
        # Wednesday
        ts = datetime(2024, 5, 22, 12, 0, tzinfo=timezone.utc)
        assert ef._check_session(ts) is True

    def test_session_fail(self):
        ef = ExecutionFilter()
        # Saturday
        ts = datetime(2024, 5, 25, 12, 0, tzinfo=timezone.utc)
        assert ef._check_session(ts) is False

    def test_drawdown_fail(self, base_df):
        ef = ExecutionFilter()
        decision = ef.validate(base_df, 1, 0.8, 0.20)
        assert decision.signal == 0
        assert decision.blocked_by == "DRAWDOWN_LIMIT"

    def test_full_cascade_pass(self, base_df):
        ef = ExecutionFilter()
        # Wednesday
        ts = datetime(2024, 5, 22, 12, 0, tzinfo=timezone.utc)
        decision = ef.validate(base_df, 1, 0.85, 0.05, timestamp=ts)
        assert decision.signal == 1
        assert decision.blocked_by is None
        assert decision.confidence_score == 0.85

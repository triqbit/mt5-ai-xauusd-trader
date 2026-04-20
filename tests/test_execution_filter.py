"""
Unit tests for the 6-layer execution filter.
"""

from unittest.mock import MagicMock

import numpy as np
import pandas as pd
import pytest

from src.trading.execution_filter import ExecutionFilter


@pytest.fixture
def mock_config():
    config = MagicMock()
    config.max_drawdown = 0.10
    return config


@pytest.fixture
def execution_filter(mock_config):
    return ExecutionFilter(mock_config)


def create_mock_df(n=300, trend="up", vol="high"):
    np.random.seed(42)
    if trend == "up":
        close = np.linspace(100, 200, n) + np.random.normal(0, 0.1, n)
    else:
        close = np.linspace(200, 100, n) + np.random.normal(0, 0.1, n)

    if vol == "high":
        high = close + 1.0
        low = close - 0.5
    else:
        high = close + 0.1
        low = close - 0.1

    df = pd.DataFrame(
        {"open": close, "high": high, "low": low, "close": close},
        index=pd.date_range("2023-01-01", periods=n, freq="h"),
    )
    return df


def test_atr_volatility(execution_filter):
    high_vol_df = create_mock_df(vol="high")
    # ATR should be around 1.5
    assert bool(execution_filter._check_atr_volatility(high_vol_df, min_atr=0.5)) is True

    low_vol_df = create_mock_df(vol="low")
    # ATR should be around 0.43
    assert bool(execution_filter._check_atr_volatility(low_vol_df, min_atr=0.5)) is False


def test_trend_angle(execution_filter):
    up_df = create_mock_df(trend="up")
    assert bool(execution_filter._check_trend_angle(up_df, 1)) is True
    assert bool(execution_filter._check_trend_angle(up_df, -1)) is False

    down_df = create_mock_df(trend="down")
    assert bool(execution_filter._check_trend_angle(down_df, -1)) is True
    assert bool(execution_filter._check_trend_angle(down_df, 1)) is False


def test_ema_sequence(execution_filter):
    # Buy: 20 > 50 > 200
    up_df = create_mock_df(n=500, trend="up")
    assert bool(execution_filter._check_ema_sequence(up_df, 1)) is True

    # Sell: 20 < 50 < 200
    down_df = create_mock_df(n=500, trend="down")
    assert bool(execution_filter._check_ema_sequence(down_df, -1)) is True


def test_momentum_rsi(execution_filter):
    # Use more data and some noise to let RSI settle
    np.random.seed(42)
    n = 200
    close_bullish = np.linspace(100, 110, n) + np.random.normal(0, 0.1, n)
    df_bullish = pd.DataFrame({"close": close_bullish})
    assert bool(execution_filter._check_momentum(df_bullish, 1)) is True

    close_bearish = np.linspace(110, 100, n) + np.random.normal(0, 0.1, n)
    df_bearish = pd.DataFrame({"close": close_bearish})
    assert bool(execution_filter._check_momentum(df_bearish, -1)) is True


def test_session_filter(execution_filter, monkeypatch):
    from datetime import datetime

    # Test Wednesday 14:00 (Open)
    with monkeypatch.context() as m:
        m.setattr(
            "src.trading.execution_filter.datetime",
            MagicMock(utcnow=lambda: datetime(2023, 1, 4, 14, 0)),
        )
        assert execution_filter._check_session_filter() is True

    # Test Saturday (Closed)
    with monkeypatch.context() as m:
        m.setattr(
            "src.trading.execution_filter.datetime",
            MagicMock(utcnow=lambda: datetime(2023, 1, 7, 14, 0)),
        )
        assert execution_filter._check_session_filter() is False


def test_drawdown_breaker(execution_filter):
    assert execution_filter._check_drawdown(0.05) is True
    assert execution_filter._check_drawdown(0.15) is False


def test_full_validation_cascade(execution_filter, monkeypatch):
    from datetime import datetime

    up_df = create_mock_df(n=500, trend="up", vol="high")

    # Ensure session is open
    monkeypatch.setattr(
        "src.trading.execution_filter.datetime",
        MagicMock(utcnow=lambda: datetime(2023, 1, 4, 14, 0)),
    )

    # Valid buy signal
    decision = execution_filter.validate(up_df, direction=1, current_drawdown=0.02, confidence=0.85)
    assert decision.signal is True
    assert decision.blocked_by is None

    # Blocked by drawdown
    decision = execution_filter.validate(up_df, direction=1, current_drawdown=0.12, confidence=0.85)
    assert decision.signal is False
    assert decision.blocked_by == "Drawdown Circuit Breaker"

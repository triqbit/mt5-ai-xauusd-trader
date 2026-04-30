"""
Unit tests for the ExecutionFilter class.
"""
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

from src.trading.execution_filter import ExecutionFilter, ExecutionDecision
from src.trading.risk_manager import TradeSignal
from src.core.config import TradingConfig

@pytest.fixture
def mock_config():
    config = MagicMock(spec=TradingConfig)
    config.confidence_threshold = 0.6
    return config

@pytest.fixture
def execution_filter(mock_config):
    return ExecutionFilter(mock_config)

@pytest.fixture
def base_signal():
    return TradeSignal(
        symbol="XAUUSD",
        direction=1,
        entry_price=2000.0,
        stop_loss=1980.0,
        take_profit=2040.0,
        lot_size=0.1,
        algorithm="ensemble",
        confidence=0.75
    )

def create_mock_df(n_bars=250, trend="up", volatility="normal"):
    """Helper to create mock market data."""
    data = {
        "open": np.linspace(1900, 2100, n_bars),
        "high": np.linspace(1910, 2110, n_bars),
        "low": np.linspace(1890, 2090, n_bars),
        "close": np.linspace(1900, 2100, n_bars),
        "tick_volume": [1000] * n_bars
    }

    if trend == "down":
        data["close"] = np.linspace(2100, 1900, n_bars)
        data["open"] = data["close"]
        data["high"] = data["close"] + 10
        data["low"] = data["close"] - 10

    if volatility == "high":
        # Introduce a massive spike in high-low range at the end
        data["high"][-1] = data["high"][-1] + 500
        data["low"][-1] = data["low"][-1] - 500

    df = pd.DataFrame(data)
    return df

def test_atr_volatility_pass(execution_filter):
    df = create_mock_df(volatility="normal")
    assert execution_filter._check_atr_volatility(df) is True

def test_atr_volatility_block(execution_filter):
    df = create_mock_df(volatility="high")
    assert execution_filter._check_atr_volatility(df) is False

def test_trend_angle_buy_pass(execution_filter):
    df = create_mock_df(trend="up")
    assert execution_filter._check_trend_angle(df, direction=1) is True

def test_trend_angle_buy_block(execution_filter):
    df = create_mock_df(trend="down")
    assert execution_filter._check_trend_angle(df, direction=1) is False

def test_ema_sequence_buy_pass(execution_filter):
    # Upward linear trend should naturally have EMA20 > EMA50 > EMA200
    df = create_mock_df(n_bars=300, trend="up")
    assert execution_filter._check_ema_sequence(df, direction=1) is True

def test_ema_sequence_buy_block(execution_filter):
    df = create_mock_df(n_bars=300, trend="down")
    assert execution_filter._check_ema_sequence(df, direction=1) is False

def test_momentum_buy_pass(execution_filter):
    # Create DF where RSI is around 60
    df = create_mock_df(n_bars=50)
    # Adjust last few closes to nudge RSI
    df.loc[df.index[-14:], "close"] = [2000 + i*2 for i in range(14)]
    assert execution_filter._check_momentum(df, direction=1) is True

def test_momentum_buy_block_overbought(execution_filter):
    df = create_mock_df(n_bars=50)
    df.loc[df.index[-14:], "close"] = [2000 + i*100 for i in range(14)]
    # RSI will be very high (> 75)
    assert execution_filter._check_momentum(df, direction=1) is False

def test_session_time_pass():
    # Wednesday 12:00 GMT
    with patch("src.trading.execution_filter.datetime") as mock_date:
        mock_date.now.return_value = datetime(2024, 5, 22, 12, 0, tzinfo=timezone.utc)
        mock_date.timezone = timezone
        ef = ExecutionFilter(MagicMock())
        assert ef._check_session_time() is True

def test_session_time_block_weekend():
    # Saturday 12:00 GMT
    with patch("src.trading.execution_filter.datetime") as mock_date:
        mock_date.now.return_value = datetime(2024, 5, 25, 12, 0, tzinfo=timezone.utc)
        mock_date.timezone = timezone
        ef = ExecutionFilter(MagicMock())
        assert ef._check_session_time() is False

def test_drawdown_pass(execution_filter):
    stats = {"balance": 9500, "peak_equity": 10000} # 5% drawdown
    assert execution_filter._check_drawdown(stats) is True

def test_drawdown_block(execution_filter):
    stats = {"balance": 8000, "peak_equity": 10000} # 20% drawdown
    assert execution_filter._check_drawdown(stats) is False

def test_full_validation_pass(execution_filter, base_signal):
    # Create a DF that should pass all filters
    # We will mock the individual check methods to ensure the integration logic works
    df = create_mock_df(n_bars=300, trend="up")
    stats = {"balance": 10000, "peak_equity": 10000}

    with patch.object(ExecutionFilter, '_check_atr_volatility', return_value=True), \
         patch.object(ExecutionFilter, '_check_trend_angle', return_value=True), \
         patch.object(ExecutionFilter, '_check_ema_sequence', return_value=True), \
         patch.object(ExecutionFilter, '_check_momentum', return_value=True), \
         patch.object(ExecutionFilter, '_check_session_time', return_value=True), \
         patch.object(ExecutionFilter, '_check_drawdown', return_value=True):

        decision = execution_filter.validate(base_signal, df, stats)
        assert decision.is_approved is True
        assert decision.blocked_by is None

def test_full_validation_block(execution_filter, base_signal):
    df = create_mock_df(volatility="high")
    stats = {"balance": 10000, "peak_equity": 10000}

    decision = execution_filter.validate(base_signal, df, stats)
    assert decision.is_approved is False
    assert decision.blocked_by == "ATR_VOLATILITY"

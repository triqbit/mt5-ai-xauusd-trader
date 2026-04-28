"""
MT5 AI/ML Trading Bot - Enterprise Edition
tests/test_execution_filter.py
Unit tests for institutional execution filter cascade.
"""

from datetime import datetime, time, timezone

import pandas as pd
import pytest

from src.trading.execution_filter import ExecutionFilter
from src.trading.risk_manager import TradeSignal


@pytest.fixture
def execution_filter():
    return ExecutionFilter()


@pytest.fixture
def base_signal():
    return TradeSignal(
        symbol="XAUUSD",
        direction=1,
        entry_price=2000.0,
        stop_loss=1990.0,
        take_profit=2020.0,
        lot_size=0.1,
        algorithm="test",
        confidence=0.8,
        timestamp=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
    )


@pytest.fixture
def mock_market_data():
    data = {
        "ATR": [1.0] * 31,
        "EMA_20": [2000.0] * 31,
        "EMA_50": [1990.0] * 31,
        "EMA_200": [1950.0] * 31,
        "RSI": [55.0] * 31,
    }
    # Adjust last two for trend angle
    data["EMA_50"][29] = 1989.0
    data["EMA_50"][30] = 1990.0
    return pd.DataFrame(data)


def test_atr_volatility_filter(execution_filter, base_signal, mock_market_data):
    # Pass case
    decision = execution_filter.validate(base_signal, mock_market_data, 0.05)
    assert decision.is_allowed

    # Block case: ATR spike
    mock_market_data.loc[30, "ATR"] = 4.0 # > 3 * 1.0
    decision = execution_filter.validate(base_signal, mock_market_data, 0.05)
    assert not decision.is_allowed
    assert decision.blocked_by == "ATR_VOLATILITY"


def test_trend_angle_filter(execution_filter, base_signal, mock_market_data):
    # Pass case (Buy direction, EMA_50 rising)
    decision = execution_filter.validate(base_signal, mock_market_data, 0.05)
    assert decision.is_allowed

    # Block case: Buy direction, EMA_50 falling
    mock_market_data.loc[30, "EMA_50"] = 1988.0 # < 1989.0
    decision = execution_filter.validate(base_signal, mock_market_data, 0.05)
    assert not decision.is_allowed
    assert decision.blocked_by == "TREND_ANGLE"

    # Pass case (Sell direction, EMA_50 falling)
    base_signal.direction = -1
    # Adjust EMAs for bearish sequence to pass EMA_SEQUENCE filter
    mock_market_data.loc[30, "EMA_20"] = 1900.0
    mock_market_data.loc[30, "EMA_50"] = 1910.0
    mock_market_data.loc[29, "EMA_50"] = 1911.0
    mock_market_data.loc[30, "EMA_200"] = 1950.0
    mock_market_data.loc[30, "RSI"] = 45.0 # Pass MOMENTUM for sell
    decision = execution_filter.validate(base_signal, mock_market_data, 0.05)
    assert decision.is_allowed


def test_ema_sequence_filter(execution_filter, base_signal, mock_market_data):
    # Pass case (Buy: 20 > 50 > 200)
    decision = execution_filter.validate(base_signal, mock_market_data, 0.05)
    assert decision.is_allowed

    # Block case (Buy: out of sequence)
    mock_market_data.loc[30, "EMA_20"] = 1900.0 # < EMA_50 (1990)
    decision = execution_filter.validate(base_signal, mock_market_data, 0.05)
    assert not decision.is_allowed
    assert decision.blocked_by == "EMA_SEQUENCE"


def test_momentum_filter(execution_filter, base_signal, mock_market_data):
    # Pass case (Buy: RSI > 50)
    decision = execution_filter.validate(base_signal, mock_market_data, 0.05)
    assert decision.is_allowed

    # Block case (Buy: RSI < 50)
    mock_market_data.loc[30, "RSI"] = 45.0
    decision = execution_filter.validate(base_signal, mock_market_data, 0.05)
    assert not decision.is_allowed
    assert decision.blocked_by == "MOMENTUM"


def test_session_filter(execution_filter, base_signal, mock_market_data):
    # Pass case (12:00 GMT)
    decision = execution_filter.validate(base_signal, mock_market_data, 0.05)
    assert decision.is_allowed

    # Block case (05:00 GMT)
    base_signal.timestamp = datetime(2024, 1, 1, 5, 0, tzinfo=timezone.utc)
    decision = execution_filter.validate(base_signal, mock_market_data, 0.05)
    assert not decision.is_allowed
    assert decision.blocked_by == "SESSION_CLOSED"


def test_drawdown_filter(execution_filter, base_signal, mock_market_data):
    # Pass case (5% drawdown)
    decision = execution_filter.validate(base_signal, mock_market_data, 0.05)
    assert decision.is_allowed

    # Block case (20% drawdown)
    decision = execution_filter.validate(base_signal, mock_market_data, 0.20)
    assert not decision.is_allowed
    assert decision.blocked_by == "DRAWDOWN_LIMIT"

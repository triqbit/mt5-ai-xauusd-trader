"""
Tests for the ExecutionFilter class.
"""
from datetime import datetime, time

import pandas as pd
import pytest

from src.trading.execution_filter import ExecutionFilter
from src.trading.risk_manager import TradeSignal


@pytest.fixture
def execution_filter():
    return ExecutionFilter()


@pytest.fixture
def base_market_data():
    data = {
        "ATR": [10.0, 10.0],
        "ATR_SMA_30": [10.0, 10.0],
        "EMA_20": [100.0, 101.0],
        "EMA_50": [90.0, 91.0],
        "EMA_200": [80.0, 81.0],
        "RSI": [60.0, 60.0],
    }
    return pd.DataFrame(data)


@pytest.fixture
def buy_signal():
    return TradeSignal(
        symbol="XAUUSD",
        direction=1,
        entry_price=2000.0,
        stop_loss=1990.0,
        take_profit=2020.0,
        lot_size=0.1,
        algorithm="ensemble",
        confidence=0.8,
        timestamp=datetime(2024, 5, 22, 10, 0),  # Wednesday 10:00 GMT
    )


@pytest.fixture
def sell_signal():
    return TradeSignal(
        symbol="XAUUSD",
        direction=-1,
        entry_price=2000.0,
        stop_loss=2010.0,
        take_profit=1980.0,
        lot_size=0.1,
        algorithm="ensemble",
        confidence=0.8,
        timestamp=datetime(2024, 5, 22, 10, 0),  # Wednesday 10:00 GMT
    )


def test_validate_all_pass(execution_filter, buy_signal, base_market_data):
    decision = execution_filter.validate(buy_signal, base_market_data, 0.05)
    assert decision.is_allowed
    assert decision.blocked_by is None
    assert decision.confidence_score == 0.8


def test_atr_volatility_fail(execution_filter, buy_signal, base_market_data):
    base_market_data.loc[1, "ATR"] = 40.0  # 4x ATR_SMA_30
    decision = execution_filter.validate(buy_signal, base_market_data, 0.05)
    assert not decision.is_allowed
    assert decision.blocked_by == "ATR Volatility Threshold exceeded"
    assert decision.confidence_score == 0.0


def test_trend_angle_fail(execution_filter, buy_signal, base_market_data):
    base_market_data.loc[1, "EMA_20"] = 99.0  # Negative slope for Buy
    decision = execution_filter.validate(buy_signal, base_market_data, 0.05)
    assert not decision.is_allowed
    assert decision.blocked_by == "Trend Angle alignment failed"
    assert decision.confidence_score == 0.2


def test_ema_sequence_fail_buy(execution_filter, buy_signal, base_market_data):
    base_market_data.loc[1, "EMA_50"] = 110.0  # EMA_20 < EMA_50
    decision = execution_filter.validate(buy_signal, base_market_data, 0.05)
    assert not decision.is_allowed
    assert decision.blocked_by == "EMA Sequence misalignment"


def test_ema_sequence_fail_sell(execution_filter, sell_signal, base_market_data):
    # Setup market data for valid Sell: EMA_20 < EMA_50 < EMA_200
    base_market_data["EMA_20"] = [80.0, 79.0]
    base_market_data["EMA_50"] = [90.0, 89.0]
    base_market_data["EMA_200"] = [100.0, 99.0]
    base_market_data["RSI"] = [40.0, 40.0]

    # Invalidate by making EMA_20 > EMA_50
    # Must keep trend slope negative for sell to pass Layer 2
    base_market_data.loc[0, "EMA_20"] = 96.0
    base_market_data.loc[1, "EMA_20"] = 95.0

    decision = execution_filter.validate(sell_signal, base_market_data, 0.05)
    assert not decision.is_allowed
    assert decision.blocked_by == "EMA Sequence misalignment"


def test_momentum_fail_buy_overextended(execution_filter, buy_signal, base_market_data):
    base_market_data.loc[1, "RSI"] = 75.0  # Too high for Buy
    decision = execution_filter.validate(buy_signal, base_market_data, 0.05)
    assert not decision.is_allowed
    assert decision.blocked_by == "Momentum Filter failed (RSI)"


def test_momentum_fail_sell_too_low(execution_filter, sell_signal, base_market_data):
    # Setup for valid Sell
    base_market_data["EMA_20"] = [80.0, 79.0]
    base_market_data["EMA_50"] = [90.0, 89.0]
    base_market_data["EMA_200"] = [100.0, 99.0]

    base_market_data.loc[1, "RSI"] = 25.0  # Too low for Sell
    decision = execution_filter.validate(sell_signal, base_market_data, 0.05)
    assert not decision.is_allowed
    assert decision.blocked_by == "Momentum Filter failed (RSI)"


def test_session_time_fail_friday_close(execution_filter, buy_signal, base_market_data):
    buy_signal.timestamp = datetime(2024, 5, 24, 15, 0)  # Friday 15:00 GMT
    decision = execution_filter.validate(buy_signal, base_market_data, 0.05)
    assert not decision.is_allowed
    assert decision.blocked_by == "Prohibited trading hours"


def test_session_time_fail_saturday(execution_filter, buy_signal, base_market_data):
    buy_signal.timestamp = datetime(2024, 5, 25, 10, 0)  # Saturday
    decision = execution_filter.validate(buy_signal, base_market_data, 0.05)
    assert not decision.is_allowed
    assert decision.blocked_by == "Prohibited trading hours"


def test_session_time_fail_sunday_early(execution_filter, buy_signal, base_market_data):
    buy_signal.timestamp = datetime(2024, 5, 26, 16, 0)  # Sunday 16:00 GMT
    decision = execution_filter.validate(buy_signal, base_market_data, 0.05)
    assert not decision.is_allowed
    assert decision.blocked_by == "Prohibited trading hours"


def test_drawdown_circuit_breaker_fail(execution_filter, buy_signal, base_market_data):
    decision = execution_filter.validate(buy_signal, base_market_data, 0.30)  # 30% DD
    assert not decision.is_allowed
    assert decision.blocked_by == "Drawdown Circuit Breaker active"

"""
Unit tests for the ExecutionFilter cascade.
"""

from datetime import datetime, time

import pandas as pd
import pytest

from src.trading.execution_filter import ExecutionFilter
from src.trading.risk_manager import TradeSignal


@pytest.fixture
def base_df():
    """Create a base DataFrame with required columns."""
    # For trend angle we need at least 3 rows
    # For ATR average we need 30 rows + 1 current
    n = 31
    data = {
        "atr": [1.0] * n,
        "ema_50": [100.0] * (n - 3) + [100.0, 100.1, 100.2],
        "ema_20": [101.0] * n,
        "ema_200": [99.0] * n,
        "rsi": [55.0] * n,
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
        algorithm="test",
        confidence=0.7,
        timestamp=datetime(2023, 1, 1, 12, 0),  # Mid-session
    )


def test_drawdown_circuit_breaker(buy_signal, base_df):
    # Pass
    filter_ok = ExecutionFilter(drawdown_pct=0.10)
    decision = filter_ok.validate(buy_signal, base_df)
    assert decision.is_approved is True

    # Fail
    filter_fail = ExecutionFilter(drawdown_pct=0.16)
    decision = filter_fail.validate(buy_signal, base_df)
    assert decision.is_approved is False
    assert decision.blocked_by == "Circuit Breaker"


def test_session_filter(buy_signal, base_df):
    # Pass: 12:00
    filter_layer = ExecutionFilter()
    decision = filter_layer.validate(buy_signal, base_df)
    assert decision.is_approved is True

    # Fail: 04:00
    buy_signal.timestamp = datetime(2023, 1, 1, 4, 0)
    decision = filter_layer.validate(buy_signal, base_df)
    assert decision.is_approved is False
    assert decision.blocked_by == "Session Filter"

    # Fail: 22:00
    buy_signal.timestamp = datetime(2023, 1, 1, 22, 0)
    decision = filter_layer.validate(buy_signal, base_df)
    assert decision.is_approved is False
    assert decision.blocked_by == "Session Filter"


def test_atr_volatility_filter(buy_signal, base_df):
    filter_layer = ExecutionFilter()

    # Pass: current ATR (1.0) < 3 * average ATR (1.0)
    decision = filter_layer.validate(buy_signal, base_df)
    assert decision.is_approved is True

    # Fail: current ATR spikes
    base_df.loc[30, "atr"] = 4.0  # 4.0 > 3 * 1.0 (approx)
    # Actually avg was 1.0, new avg with 4.0 is slightly higher but 4.0 still > 3 * old_avg
    decision = filter_layer.validate(buy_signal, base_df)
    assert decision.is_approved is False
    assert decision.blocked_by == "ATR Volatility"


def test_trend_angle_filter(buy_signal, base_df):
    filter_layer = ExecutionFilter()

    # Pass: Buy signal, EMA 50 slope positive
    base_df.loc[30, "ema_50"] = 100.5
    base_df.loc[28, "ema_50"] = 100.0  # index -3
    decision = filter_layer.validate(buy_signal, base_df)
    assert decision.is_approved is True

    # Fail: Buy signal, EMA 50 slope negative
    base_df.loc[30, "ema_50"] = 99.5
    base_df.loc[28, "ema_50"] = 100.0
    decision = filter_layer.validate(buy_signal, base_df)
    assert decision.is_approved is False
    assert decision.blocked_by == "Trend Angle"

    # Sell signal
    sell_signal = buy_signal
    sell_signal.direction = -1

    # Pass: Sell signal, EMA 50 slope negative
    base_df.loc[30, "ema_50"] = 99.5
    base_df.loc[28, "ema_50"] = 100.0
    # But wait, other filters might fail now (EMA sequence, RSI)
    # Let's mock the other indicators for sell
    base_df["ema_20"] = 90.0
    base_df["ema_50"] = 100.0
    base_df["ema_200"] = 110.0
    base_df["rsi"] = 40.0
    base_df.loc[30, "ema_50"] = 99.0
    base_df.loc[28, "ema_50"] = 100.0 # slope -1.0

    decision = filter_layer.validate(sell_signal, base_df)
    assert decision.is_approved is True


def test_ema_sequence_filter(buy_signal, base_df):
    filter_layer = ExecutionFilter()

    # Pass: 20 (101) > 50 (100) > 200 (99)
    base_df["ema_20"] = 101.0
    base_df["ema_50"] = 100.0
    base_df["ema_200"] = 99.0
    # Also need to ensure Trend Angle passes: slope of ema_50 must be positive for Buy
    base_df.loc[30, "ema_50"] = 100.1
    base_df.loc[28, "ema_50"] = 100.0

    decision = filter_layer.validate(buy_signal, base_df)
    assert decision.is_approved is True

    # Fail: 20 < 50
    base_df.loc[30, "ema_20"] = 99.0
    decision = filter_layer.validate(buy_signal, base_df)
    assert decision.is_approved is False
    assert decision.blocked_by == "EMA Sequence"


def test_momentum_filter(buy_signal, base_df):
    filter_layer = ExecutionFilter()

    # Pass: Buy RSI 55 > 50
    base_df["rsi"] = 55.0
    decision = filter_layer.validate(buy_signal, base_df)
    assert decision.is_approved is True

    # Fail: Buy RSI 45 < 50
    base_df.loc[30, "rsi"] = 45.0
    decision = filter_layer.validate(buy_signal, base_df)
    assert decision.is_approved is False
    assert decision.blocked_by == "Momentum Filter"

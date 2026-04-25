"""
Unit tests for the ExecutionFilter cascade.
"""
from __future__ import annotations

from datetime import datetime, timezone
import pandas as pd
import pytest
from src.trading.execution_filter import ExecutionFilter, ExecutionDecision
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
        algorithm="ensemble",
        confidence=0.8,
    )

@pytest.fixture
def mock_indicators():
    return pd.DataFrame({
        "atr_14": [1.0, 1.2],
        "atr_14_ma_100": [1.0, 1.0],
        "ema_20": [2010.0, 2015.0],
        "ema_50": [2005.0, 2010.0],
        "ema_200": [1990.0, 1995.0],
        "rsi_14": [55.0, 60.0],
    })

def test_atr_volatility_layer(execution_filter, base_signal, mock_indicators):
    # Pass: ATR 1.2 <= 3 * 1.0
    assert bool(execution_filter._validate_atr_volatility(mock_indicators)) is True

    # Fail: ATR 4.0 > 3 * 1.0
    fail_df = mock_indicators.copy()
    fail_df.loc[1, "atr_14"] = 4.0
    assert bool(execution_filter._validate_atr_volatility(fail_df)) is False

def test_trend_angle_layer(execution_filter, base_signal, mock_indicators):
    # Pass: Buy signal, EMA 50 increasing (2010 > 2005)
    assert bool(execution_filter._validate_trend_angle(base_signal, mock_indicators)) is True

    # Fail: Buy signal, EMA 50 decreasing (2000 < 2005)
    fail_df = mock_indicators.copy()
    fail_df.loc[1, "ema_50"] = 2000.0
    assert bool(execution_filter._validate_trend_angle(base_signal, fail_df)) is False

    # Pass: Sell signal, EMA 50 decreasing
    sell_signal = base_signal
    sell_signal.direction = -1
    assert bool(execution_filter._validate_trend_angle(sell_signal, fail_df)) is True

def test_ema_sequence_layer(execution_filter, base_signal, mock_indicators):
    # Pass: Buy signal, 2015 > 2010 > 1995
    assert bool(execution_filter._validate_ema_sequence(base_signal, mock_indicators)) is True

    # Fail: Buy signal, sequence broken
    fail_df = mock_indicators.copy()
    fail_df.loc[1, "ema_20"] = 1900.0
    assert bool(execution_filter._validate_ema_sequence(base_signal, fail_df)) is False

    # Pass: Sell signal, 1900 < 2010 < 2020
    sell_signal = base_signal
    sell_signal.direction = -1
    sell_df = pd.DataFrame(
        {"ema_20": [1900.0], "ema_50": [1950.0], "ema_200": [2000.0]}
    )
    assert bool(execution_filter._validate_ema_sequence(sell_signal, sell_df)) is True

def test_momentum_layer(execution_filter, base_signal, mock_indicators):
    # Pass: Buy signal, RSI 60 > 50
    assert bool(execution_filter._validate_momentum(base_signal, mock_indicators)) is True

    # Fail: Buy signal, RSI 40 < 50
    fail_df = mock_indicators.copy()
    fail_df.loc[1, "rsi_14"] = 40.0
    assert bool(execution_filter._validate_momentum(base_signal, fail_df)) is False

    # Pass: Sell signal, RSI 40 < 50
    sell_signal = base_signal
    sell_signal.direction = -1
    assert bool(execution_filter._validate_momentum(sell_signal, fail_df)) is True

def test_session_layer(execution_filter):
    # Pass: 12:00 GMT
    ts_pass = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
    assert execution_filter._validate_session(ts_pass) is True

    # Fail: 02:00 GMT
    ts_fail = datetime(2024, 1, 1, 2, 0, tzinfo=timezone.utc)
    assert execution_filter._validate_session(ts_fail) is False

    # Fail: 22:00 GMT
    ts_fail2 = datetime(2024, 1, 1, 22, 0, tzinfo=timezone.utc)
    assert execution_filter._validate_session(ts_fail2) is False

def test_drawdown_layer(execution_filter):
    # Pass: 5% drawdown
    assert execution_filter._validate_drawdown(0.05) is True

    # Fail: 20% drawdown
    assert execution_filter._validate_drawdown(0.20) is False

def test_full_cascade_pass(execution_filter, base_signal, mock_indicators):
    ts = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
    decision = execution_filter.validate(base_signal, mock_indicators, 0.05, timestamp=ts)
    assert decision.is_approved is True
    assert decision.blocked_by is None

def test_full_cascade_fail(execution_filter, base_signal, mock_indicators):
    ts = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)

    # Fail at ATR layer
    fail_df = mock_indicators.copy()
    fail_df.loc[1, "atr_14"] = 10.0
    decision = execution_filter.validate(base_signal, fail_df, 0.05, timestamp=ts)
    assert decision.is_approved is False
    assert decision.blocked_by == "ATR Volatility Block"

def test_missing_columns_handling(execution_filter, base_signal):
    # Should skip missing columns and pass if others are OK
    empty_df = pd.DataFrame({"some_other_col": [1, 2]})
    ts = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
    decision = execution_filter.validate(base_signal, empty_df, 0.05, timestamp=ts)
    # Since all layers with missing columns return True, it should pass
    assert decision.is_approved is True

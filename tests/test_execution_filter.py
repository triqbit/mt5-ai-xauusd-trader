"""
MT5 AI/ML Trading Bot - Enterprise Edition
tests/test_execution_filter.py
Unit tests for the 6-layer execution filter.
"""

from datetime import datetime, UTC
from unittest.mock import MagicMock

import numpy as np
import pandas as pd
import pytest

from src.trading.execution_filter import ExecutionFilter
from src.core.schemas import TradeSignal


@pytest.fixture
def base_data():
    """Generates 200 rows of neutral synthetic market data."""
    dates = pd.date_range(start="2023-01-01", periods=200, freq="5min")
    df = pd.DataFrame({
        "open": np.linspace(1800, 1800, 200),
        "high": np.linspace(1805, 1805, 200),
        "low": np.linspace(1795, 1795, 200),
        "close": np.linspace(1800, 1800, 200),
        "tick_volume": [100] * 200
    }, index=dates)
    return df

@pytest.fixture
def bullish_data(base_data):
    """Generates bullish data for EMA and trend checks."""
    df = base_data.copy()
    # Create an uptrend
    df["close"] = np.linspace(1700, 1900, 200)
    df["high"] = df["close"] + 5
    df["low"] = df["close"] - 5

    # Pre-calculate EMAs (8, 21, 50, 200)
    for p in [8, 21, 50, 200]:
        df[f"base_M5_ema_{p}"] = df["close"].ewm(span=p, adjust=False).mean()

    # Pre-calculate RSI in bullish zone (60)
    df["base_M5_rsi"] = 60

    # Pre-calculate ATR
    df["base_M5_atr"] = 1.0

    return df

@pytest.fixture
def bearish_data(base_data):
    """Generates bearish data for EMA and trend checks."""
    df = base_data.copy()
    # Create a downtrend
    df["close"] = np.linspace(1900, 1700, 200)
    df["high"] = df["close"] + 5
    df["low"] = df["close"] - 5

    # Pre-calculate EMAs (8, 21, 50, 200)
    for p in [8, 21, 50, 200]:
        df[f"base_M5_ema_{p}"] = df["close"].ewm(span=p, adjust=False).mean()

    # Pre-calculate RSI in bearish zone (40)
    df["base_M5_rsi"] = 40

    # Pre-calculate ATR
    df["base_M5_atr"] = 1.0

    return df

@pytest.fixture
def filter_engine():
    return ExecutionFilter(max_drawdown=0.12)

@pytest.fixture
def valid_timestamp():
    return datetime(2023, 10, 10, 10, 0, 0, tzinfo=UTC) # Tuesday

@pytest.fixture
def buy_signal(valid_timestamp):
    return TradeSignal(
        symbol="XAUUSD",
        direction=1,
        entry_price=1850,
        stop_loss=1840,
        take_profit=1870,
        lot_size=0.1,
        algorithm="ensemble",
        confidence=0.8,
        timestamp=valid_timestamp
    )

@pytest.fixture
def sell_signal(valid_timestamp):
    return TradeSignal(
        symbol="XAUUSD",
        direction=-1,
        entry_price=1850,
        stop_loss=1860,
        take_profit=1830,
        lot_size=0.1,
        algorithm="ensemble",
        confidence=0.8,
        timestamp=valid_timestamp
    )

# --- Layer 1: ATR Volatility ---
def test_atr_volatility_pass(filter_engine, base_data):
    df = base_data.copy()
    df["base_M5_atr"] = 1.0
    passed, metrics = filter_engine._check_atr_volatility_with_metrics(df)
    assert passed is True
    assert metrics["ratio"] <= 3.0

def test_atr_volatility_fail(filter_engine, base_data):
    df = base_data.copy()
    # Mock ATR: 1.0 avg, 10.0 current (ratio 10 > 3)
    df["base_M5_atr"] = [1.0] * 199 + [10.0]
    passed, metrics = filter_engine._check_atr_volatility_with_metrics(df)
    assert passed is False
    assert metrics["ratio"] > 3.0

# --- Layer 2: Trend Angle ---
def test_trend_angle_buy_pass(filter_engine, bullish_data):
    passed, metrics = filter_engine._check_trend_angle_with_metrics(bullish_data, direction=1)
    assert passed is True
    assert metrics["slope"] > 0

def test_trend_angle_sell_pass(filter_engine, bearish_data):
    passed, metrics = filter_engine._check_trend_angle_with_metrics(bearish_data, direction=-1)
    assert passed is True
    assert metrics["slope"] < 0

def test_trend_angle_fail(filter_engine, bullish_data):
    # Pass bullish data but request SELL signal
    passed, metrics = filter_engine._check_trend_angle_with_metrics(bullish_data, direction=-1)
    assert passed is False
    assert metrics["slope"] > 0

# --- Layer 3: EMA Sequence ---
def test_ema_sequence_buy_pass(filter_engine, bullish_data):
    passed, _ = filter_engine._check_ema_sequence_with_metrics(bullish_data, direction=1)
    assert passed is True

def test_ema_sequence_sell_pass(filter_engine, bearish_data):
    passed, _ = filter_engine._check_ema_sequence_with_metrics(bearish_data, direction=-1)
    assert passed is True

def test_ema_sequence_fail(filter_engine, bullish_data):
    # Mess up the sequence by making EMA 8 small
    bullish_data.loc[bullish_data.index[-1], "base_M5_ema_8"] = 100.0
    passed, _ = filter_engine._check_ema_sequence_with_metrics(bullish_data, direction=1)
    assert passed is False

# --- Layer 4: Momentum (RSI) ---
def test_momentum_buy_pass(filter_engine, bullish_data):
    passed, metrics = filter_engine._check_momentum_with_metrics(bullish_data, direction=1)
    assert passed is True
    assert 50 <= metrics["rsi"] <= 75

def test_momentum_sell_pass(filter_engine, bearish_data):
    passed, metrics = filter_engine._check_momentum_with_metrics(bearish_data, direction=-1)
    assert passed is True
    assert 25 <= metrics["rsi"] <= 50

def test_momentum_fail(filter_engine, bullish_data):
    bullish_data["base_M5_rsi"] = 80
    passed, _ = filter_engine._check_momentum_with_metrics(bullish_data, direction=1)
    assert passed is False

# --- Layer 5: Session/Time ---
def test_session_time_pass(filter_engine):
    dt = datetime(2023, 10, 10, 10, 0, 0, tzinfo=UTC) # Tuesday
    assert filter_engine._check_session_time(dt) is True

def test_session_time_fail_saturday(filter_engine):
    dt = datetime(2023, 10, 14, 10, 0, 0, tzinfo=UTC) # Saturday
    assert filter_engine._check_session_time(dt) is False

def test_session_time_fail_friday_late(filter_engine):
    dt = datetime(2023, 10, 13, 17, 0, 0, tzinfo=UTC) # Friday 17:00
    assert filter_engine._check_session_time(dt) is False

def test_session_time_pass_sunday_late(filter_engine):
    dt = datetime(2023, 10, 15, 18, 0, 0, tzinfo=UTC) # Sunday 18:00
    assert filter_engine._check_session_time(dt) is True

# --- Layer 6: Drawdown ---
def test_drawdown_pass(filter_engine):
    assert filter_engine._check_drawdown_limit(0.05) is True

def test_drawdown_fail(filter_engine):
    assert filter_engine._check_drawdown_limit(0.13) is False

# --- Layer 7: Model Stability ---
def test_model_stability_pass(filter_engine, buy_signal, bullish_data):
    health = {"drift": 0.1, "accuracy": 0.8}
    decision = filter_engine.validate(buy_signal, bullish_data, 0.05, model_health=health)
    assert decision.trace["model_stability"]["passed"] is True

def test_model_stability_fail_drift(filter_engine, buy_signal, bullish_data):
    health = {"drift": 0.4, "accuracy": 0.8}
    decision = filter_engine.validate(buy_signal, bullish_data, 0.05, model_health=health)
    assert decision.trace["model_stability"]["passed"] is False
    assert decision.blocked_by == "MODEL_STABILITY"

# --- Layer 8: Performance Floor ---
def test_performance_floor_pass(filter_engine, buy_signal, bullish_data):
    mock_logger = MagicMock()
    mock_logger.read_performance_report.return_value = {"win_rate": 0.6, "total_trades": 25}
    decision = filter_engine.validate(buy_signal, bullish_data, 0.05, trade_logger=mock_logger)
    assert decision.trace["performance_floor"]["passed"] is True

def test_performance_floor_fail(filter_engine, buy_signal, bullish_data):
    mock_logger = MagicMock()
    mock_logger.read_performance_report.return_value = {"win_rate": 0.3, "total_trades": 25}
    decision = filter_engine.validate(buy_signal, bullish_data, 0.05, trade_logger=mock_logger)
    assert decision.trace["performance_floor"]["passed"] is False
    assert decision.blocked_by == "PERFORMANCE_FLOOR"

def test_performance_floor_ignored_if_few_trades(filter_engine, buy_signal, bullish_data):
    mock_logger = MagicMock()
    mock_logger.read_performance_report.return_value = {"win_rate": 0.1, "total_trades": 5}
    decision = filter_engine.validate(buy_signal, bullish_data, 0.05, trade_logger=mock_logger)
    assert decision.trace["performance_floor"]["passed"] is True

# --- Layer 9: Confidence Threshold ---
def test_confidence_fail(filter_engine, bullish_data, valid_timestamp):
    low_conf_signal = TradeSignal(
        symbol="XAUUSD", direction=1, entry_price=1850, stop_loss=1840, take_profit=1870,
        lot_size=0.1, algorithm="ensemble", confidence=0.4, timestamp=valid_timestamp
    )
    decision = filter_engine.validate(low_conf_signal, bullish_data, 0.05)
    assert decision.trace["confidence_threshold"]["passed"] is False
    assert decision.blocked_by == "CONFIDENCE_THRESHOLD"

# --- Layer 10: Signal Consistency ---
def test_signal_consistency_fail(filter_engine, buy_signal, bullish_data):
    # Simulate flipping signals: 1, -1, 1, -1, 1
    filter_engine.validate(buy_signal, bullish_data, 0.05) # 1
    sell_sig = buy_signal.model_copy(update={"direction": -1, "stop_loss": 1860, "take_profit": 1830})
    filter_engine.validate(sell_sig, bullish_data, 0.05) # -1
    filter_engine.validate(buy_signal, bullish_data, 0.05) # 1
    filter_engine.validate(sell_sig, bullish_data, 0.05) # -1
    decision = filter_engine.validate(buy_signal, bullish_data, 0.05) # 1
    # Changes: 1->-1, -1->1, 1->-1, -1->1 => 4 changes. Default max is 3.
    assert decision.trace["signal_consistency"]["passed"] is False
    assert decision.blocked_by == "SIGNAL_CONSISTENCY"

# --- Full Cascade ---
def test_full_cascade_pass(filter_engine, buy_signal, bullish_data):
    ts = datetime(2023, 10, 10, 10, 0, 0, tzinfo=UTC)
    decision = filter_engine.validate(buy_signal, bullish_data, 0.05, timestamp=ts)
    assert decision.is_approved is True
    assert decision.blocked_by is None

def test_full_cascade_blocked_by_session(filter_engine, buy_signal, bullish_data):
    ts = datetime(2023, 10, 14, 10, 0, 0, tzinfo=UTC) # Saturday
    decision = filter_engine.validate(buy_signal, bullish_data, 0.05, timestamp=ts)
    assert decision.is_approved is False
    assert decision.blocked_by == "SESSION_CLOSED"

def test_full_cascade_blocked_by_drawdown(filter_engine, buy_signal, bullish_data):
    ts = datetime(2023, 10, 10, 10, 0, 0, tzinfo=UTC)
    decision = filter_engine.validate(buy_signal, bullish_data, 0.15, timestamp=ts)
    assert decision.is_approved is False
    assert decision.blocked_by == "DRAWDOWN_LIMIT"

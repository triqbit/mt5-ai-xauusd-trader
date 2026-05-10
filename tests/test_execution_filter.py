"""
MT5 AI/ML Trading Bot - Enterprise Edition
tests/test_execution_filter.py
Unit tests for the 6-layer execution filter.
"""

from datetime import datetime

import numpy as np
import pandas as pd
import pytest

from src.core.config import TradingConfig
from src.core.schemas import TradeSignal
from src.trading.execution_filter import ExecutionFilter


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
def buy_signal():
    return TradeSignal(
        symbol="XAUUSD",
        direction=1,
        entry_price=1850,
        stop_loss=1840,
        take_profit=1870,
        lot_size=0.1,
        algorithm="ensemble",
        confidence=0.8
    )

@pytest.fixture
def sell_signal():
    return TradeSignal(
        symbol="XAUUSD",
        direction=-1,
        entry_price=1850,
        stop_loss=1860,
        take_profit=1830,
        lot_size=0.1,
        algorithm="ensemble",
        confidence=0.8
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
    # Mock ATR: 1.0 avg, 10.0 current
    df["base_M5_atr"] = [1.0] * 199 + [10.0]
    passed, metrics = filter_engine._check_atr_volatility_with_metrics(df)
    assert passed is False
    assert metrics["ratio"] > 3.0

def test_atr_volatility_exact_limit(filter_engine):
    # Use precomputed to test exact ratio logic
    precomputed = {"current_atr": 3.0, "avg_atr": 1.0}
    passed, metrics = filter_engine._check_atr_volatility_with_metrics(None, precomputed=precomputed)
    assert passed is True
    assert metrics["ratio"] == 3.0

def test_atr_volatility_just_above_limit(filter_engine):
    # Use precomputed to test exact ratio logic
    precomputed = {"current_atr": 3.1, "avg_atr": 1.0}
    passed, metrics = filter_engine._check_atr_volatility_with_metrics(None, precomputed=precomputed)
    assert passed is False
    assert metrics["ratio"] == 3.1

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
    # Mess up the sequence
    bullish_data.loc[bullish_data.index[-1], "base_M5_ema_8"] = 0
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
    dt = datetime(2023, 10, 10, 10, 0, 0) # Tue
    assert filter_engine._check_session_time(dt) is True

def test_session_time_fail_saturday(filter_engine):
    dt = datetime(2023, 10, 14, 10, 0, 0) # Sat
    assert filter_engine._check_session_time(dt) is False

def test_session_time_friday_before_close(filter_engine):
    dt = datetime(2023, 10, 13, 15, 59, 0) # Fri 15:59
    assert filter_engine._check_session_time(dt) is True

def test_session_time_friday_after_close(filter_engine):
    dt = datetime(2023, 10, 13, 16, 1, 0) # Fri 16:01
    assert filter_engine._check_session_time(dt) is False

def test_session_time_sunday_before_open(filter_engine):
    dt = datetime(2023, 10, 15, 16, 59, 0) # Sun 16:59
    assert filter_engine._check_session_time(dt) is False

def test_session_time_sunday_after_open(filter_engine):
    dt = datetime(2023, 10, 15, 17, 1, 0) # Sun 17:01
    assert filter_engine._check_session_time(dt) is True

# --- Layer 6: Drawdown ---
def test_drawdown_pass(filter_engine):
    assert filter_engine._check_drawdown_limit(0.05) is True

def test_drawdown_fail(filter_engine):
    assert filter_engine._check_drawdown_limit(0.13) is False

def test_drawdown_exact_limit_fail(filter_engine):
    # filter_engine.max_drawdown is 0.12 by default
    assert filter_engine._check_drawdown_limit(0.12) is False

# --- Full Cascade ---
def test_full_cascade_pass(filter_engine, buy_signal, bullish_data):
    ts = datetime(2023, 10, 10, 10, 0, 0)
    decision = filter_engine.validate(buy_signal, bullish_data, 0.05, timestamp=ts)
    assert decision.is_approved is True
    assert decision.blocked_by is None
    assert decision.confidence_score == buy_signal.confidence

def test_full_cascade_blocked_by_session(filter_engine, buy_signal, bullish_data):
    ts = datetime(2023, 10, 14, 10, 0, 0) # Sat
    decision = filter_engine.validate(buy_signal, bullish_data, 0.05, timestamp=ts)
    assert decision.is_approved is False
    assert decision.blocked_by == "SESSION_CLOSED"

def test_full_cascade_blocked_by_drawdown(filter_engine, buy_signal, bullish_data):
    ts = datetime(2023, 10, 10, 10, 0, 0)
    decision = filter_engine.validate(buy_signal, bullish_data, 0.15, timestamp=ts)
    assert decision.is_approved is False
    assert decision.blocked_by == "DRAWDOWN_LIMIT"

def test_config_integration(buy_signal):
    """Verifies that ExecutionFilter correctly uses parameters from TradingConfig."""
    config = TradingConfig(
        max_drawdown=0.05,
        volatility_extreme_threshold=2.0,
        MT5_PASSWORD="fake_password",
        MT5_SERVER="fake_server"
    )
    ef = ExecutionFilter(config=config)

    # Test drawdown limit from config
    assert ef._check_drawdown_limit(0.04) is True
    assert ef._check_drawdown_limit(0.05) is False

    # Test ATR volatility threshold from config
    # ratio 2.1 should fail with threshold 2.0
    precomputed = {"current_atr": 2.1, "avg_atr": 1.0}
    passed, metrics = ef._check_atr_volatility_with_metrics(None, precomputed=precomputed)
    assert passed is False
    assert metrics["ratio"] == 2.1

def test_validate_with_precomputed_metrics_only(filter_engine, buy_signal):
    """Verifies optimization path: validate works with None market_data if metrics are provided."""
    ts = datetime(2023, 10, 10, 10, 0, 0)
    precomputed = {
        "atr_volatility": {"current_atr": 1.0, "avg_atr": 1.0},
        "trend_angle": {"slope": 1.0},
        "ema_sequence": {"emas": {8: 104, 21: 103, 50: 102, 200: 101}},
        "momentum": {"rsi": 60.0},
    }

    decision = filter_engine.validate(
        buy_signal,
        market_data=None,
        current_drawdown=0.01,
        timestamp=ts,
        precomputed_metrics=precomputed
    )

    assert decision.is_approved is True
    assert decision.trace["atr_volatility"]["passed"] is True
    assert decision.trace["trend_angle"]["passed"] is True
    assert decision.trace["ema_sequence"]["passed"] is True
    assert decision.trace["momentum"]["passed"] is True

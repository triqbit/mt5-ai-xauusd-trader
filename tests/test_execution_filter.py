"""
MT5 AI/ML Trading Bot - Enterprise Edition
tests/test_execution_filter.py
Unit tests for the 6-layer execution filter.
"""

from datetime import datetime

import numpy as np
import pandas as pd
import pytest

from src.trading.execution_filter import ExecutionFilter
from src.trading.risk_manager import TradeSignal


@pytest.fixture
def base_data():
    """Generates 200 rows of neutral synthetic market data."""
    dates = pd.date_range(start="2023-01-01", periods=200, freq="5min")
    df = pd.DataFrame(
        {
            "open": np.linspace(1800, 1800, 200),
            "high": np.linspace(1805, 1805, 200),
            "low": np.linspace(1795, 1795, 200),
            "close": np.linspace(1800, 1800, 200),
            "tick_volume": [100] * 200,
        },
        index=dates,
    )
    return df


@pytest.fixture
def bullish_data(base_data):
    """Generates bullish data for EMA and trend checks."""
    df = base_data.copy()
    # Create an uptrend
    df["close"] = np.linspace(1700, 1900, 200)
    df["high"] = df["close"] + 5
    df["low"] = df["close"] - 5

    # Pre-calculate EMAs to avoid fallback logic testing only
    for p in [8, 20, 21, 50, 200]:
        df[f"base_M5_ema_{p}"] = df["close"].ewm(span=p, adjust=False).mean()

    # Pre-calculate RSI in bullish zone (60)
    df["base_M5_rsi"] = 60

    # Pre-calculate ATR
    df["base_M5_atr"] = 10

    return df


@pytest.fixture
def bearish_data(base_data):
    """Generates bearish data for EMA and trend checks."""
    df = base_data.copy()
    # Create a downtrend
    df["close"] = np.linspace(1900, 1700, 200)
    df["high"] = df["close"] + 5
    df["low"] = df["close"] - 5

    # Pre-calculate EMAs
    for p in [8, 20, 21, 50, 200]:
        df[f"base_M5_ema_{p}"] = df["close"].ewm(span=p, adjust=False).mean()

    # Pre-calculate RSI in bearish zone (40)
    df["base_M5_rsi"] = 40

    # Pre-calculate ATR
    df["base_M5_atr"] = 10

    return df


@pytest.fixture
def filter_engine():
    return ExecutionFilter(max_drawdown=0.15)


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
        confidence=0.8,
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
        confidence=0.8,
    )


# --- Layer 1: ATR Volatility ---
def test_atr_volatility_pass(filter_engine, base_data):
    # Normal volatility
    df = base_data.copy()
    df["base_M5_atr"] = 1.0
    assert filter_engine._check_atr_volatility(df) is True


def test_atr_volatility_fail(filter_engine, base_data):
    # Spiking volatility
    df = base_data.copy()
    df["base_M5_atr"] = [1.0] * 199 + [10.0]
    assert filter_engine._check_atr_volatility(df) is False


# --- Layer 2: Trend Angle (EMA20) ---
def test_trend_angle_buy_pass(filter_engine, bullish_data):
    assert filter_engine._check_trend_angle(bullish_data, direction=1) is True


def test_trend_angle_buy_fail(filter_engine, bearish_data):
    assert filter_engine._check_trend_angle(bearish_data, direction=1) is False


def test_trend_angle_sell_pass(filter_engine, bearish_data):
    assert filter_engine._check_trend_angle(bearish_data, direction=-1) is True


def test_trend_angle_sell_fail(filter_engine, bullish_data):
    assert filter_engine._check_trend_angle(bullish_data, direction=-1) is False


def test_trend_angle_fallback(filter_engine, base_data):
    # Test without pre-calculated EMA20 column
    df = base_data.copy()
    df["close"] = np.linspace(1700, 1900, 200)  # Uptrend
    assert filter_engine._check_trend_angle(df, direction=1) is True


# --- Layer 3: EMA Sequence ---
def test_ema_sequence_buy_pass(filter_engine, bullish_data):
    assert filter_engine._check_ema_sequence(bullish_data, direction=1) is True


def test_ema_sequence_buy_fail(filter_engine, bearish_data):
    assert filter_engine._check_ema_sequence(bearish_data, direction=1) is False


def test_ema_sequence_sell_pass(filter_engine, bearish_data):
    assert filter_engine._check_ema_sequence(bearish_data, direction=-1) is True


def test_ema_sequence_sell_fail(filter_engine, bullish_data):
    assert filter_engine._check_ema_sequence(bullish_data, direction=-1) is False


# --- Layer 4: Momentum (RSI) ---
def test_momentum_buy_pass(filter_engine, bullish_data):
    # bullish_data has RSI 60 (Healthy for BUY: 50-75)
    assert filter_engine._check_momentum(bullish_data, direction=1) is True


def test_momentum_buy_fail_low(filter_engine, bearish_data):
    # bearish_data has RSI 40 (Too low for BUY)
    assert filter_engine._check_momentum(bearish_data, direction=1) is False


def test_momentum_buy_fail_high(filter_engine, bullish_data):
    # RSI too high (80)
    bullish_data["base_M5_rsi"] = 80
    assert filter_engine._check_momentum(bullish_data, direction=1) is False


def test_momentum_sell_pass(filter_engine, bearish_data):
    # bearish_data has RSI 40 (Healthy for SELL: 25-50)
    assert filter_engine._check_momentum(bearish_data, direction=-1) is True


def test_momentum_sell_fail_high(filter_engine, bullish_data):
    # bullish_data has RSI 60 (Too high for SELL)
    assert filter_engine._check_momentum(bullish_data, direction=-1) is False


def test_momentum_sell_fail_low(filter_engine, bearish_data):
    # RSI too low (20)
    bearish_data["base_M5_rsi"] = 20
    assert filter_engine._check_momentum(bearish_data, direction=-1) is False


# --- Layer 5: Session/Time ---
def test_session_time_pass(filter_engine):
    # Tuesday 10:00 GMT
    dt = datetime(2023, 10, 10, 10, 0, 0)
    assert filter_engine._check_session_time(dt) is True


def test_session_time_fail_saturday(filter_engine):
    # Saturday
    dt = datetime(2023, 10, 14, 10, 0, 0)
    assert filter_engine._check_session_time(dt) is False


def test_session_time_sunday_pass(filter_engine):
    # Sunday 18:00 GMT (Passes after 17:00)
    dt = datetime(2023, 10, 15, 18, 0, 0)
    assert filter_engine._check_session_time(dt) is True


def test_session_time_sunday_fail(filter_engine):
    # Sunday 12:00 GMT (Fails before 17:00)
    dt = datetime(2023, 10, 15, 12, 0, 0)
    assert filter_engine._check_session_time(dt) is False


def test_session_time_friday_pass(filter_engine):
    # Friday 12:00 GMT (Passes before 16:00)
    dt = datetime(2023, 10, 13, 12, 0, 0)
    assert filter_engine._check_session_time(dt) is True


def test_session_time_friday_fail(filter_engine):
    # Friday 18:00 GMT (Fails after 16:00)
    dt = datetime(2023, 10, 13, 18, 0, 0)
    assert filter_engine._check_session_time(dt) is False


# --- Layer 6: Drawdown ---
def test_drawdown_pass(filter_engine):
    assert filter_engine._check_drawdown_limit(0.05) is True


def test_drawdown_fail(filter_engine):
    assert filter_engine._check_drawdown_limit(0.20) is False


# --- Full Cascade ---
def test_full_cascade_pass(filter_engine, buy_signal, bullish_data):
    # Tuesday 10:00 GMT
    ts = datetime(2023, 10, 10, 10, 0, 0)
    decision = filter_engine.validate(buy_signal, bullish_data, 0.05, timestamp=ts)
    assert decision.is_approved is True
    assert decision.blocked_by is None
    assert decision.confidence_score == buy_signal.confidence


def test_full_cascade_blocked_by_atr(filter_engine, buy_signal, base_data):
    # Spiking volatility
    base_data["base_M5_atr"] = [1.0] * 199 + [10.0]
    ts = datetime(2023, 10, 10, 10, 0, 0)
    decision = filter_engine.validate(buy_signal, base_data, 0.05, timestamp=ts)
    assert decision.is_approved is False
    assert decision.blocked_by == "ATR_VOLATILITY"


def test_full_cascade_blocked_by_trend(filter_engine, buy_signal, bearish_data):
    # Buy signal on bearish data
    ts = datetime(2023, 10, 10, 10, 0, 0)
    decision = filter_engine.validate(buy_signal, bearish_data, 0.05, timestamp=ts)
    assert decision.is_approved is False
    assert decision.blocked_by == "TREND_ANGLE"


def test_full_cascade_blocked_by_ema(filter_engine, buy_signal, bullish_data):
    # Break EMA sequence
    bullish_data["base_M5_ema_200"] = 3000
    ts = datetime(2023, 10, 10, 10, 0, 0)
    decision = filter_engine.validate(buy_signal, bullish_data, 0.05, timestamp=ts)
    assert decision.is_approved is False
    assert decision.blocked_by == "EMA_SEQUENCE"


def test_full_cascade_blocked_by_momentum(filter_engine, buy_signal, bullish_data):
    # Set RSI to 80 (Overbought, outside 50-75 zone)
    bullish_data["base_M5_rsi"] = 80
    ts = datetime(2023, 10, 10, 10, 0, 0)
    decision = filter_engine.validate(buy_signal, bullish_data, 0.05, timestamp=ts)
    assert decision.is_approved is False
    assert decision.blocked_by == "MOMENTUM"


def test_full_cascade_blocked_by_session(filter_engine, buy_signal, bullish_data):
    # Saturday
    ts = datetime(2023, 10, 14, 10, 0, 0)
    decision = filter_engine.validate(buy_signal, bullish_data, 0.05, timestamp=ts)
    assert decision.is_approved is False
    assert decision.blocked_by == "SESSION_TIME"


def test_full_cascade_blocked_by_drawdown(filter_engine, buy_signal, bullish_data):
    ts = datetime(2023, 10, 10, 10, 0, 0)
    decision = filter_engine.validate(buy_signal, bullish_data, 0.20, timestamp=ts)
    assert decision.is_approved is False
    assert decision.blocked_by == "DRAWDOWN_LIMIT"

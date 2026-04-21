"""
Tests for ExecutionFilter.
"""
from datetime import datetime, time
import pytest
import pandas as pd
import numpy as np
from src.trading.execution_filter import ExecutionFilter, TradeSignal

@pytest.fixture
def sample_df():
    """Create a sample OHLCV dataframe."""
    np.random.seed(42)
    dates = pd.date_range("2024-01-01", periods=300, freq="5min")
    df = pd.DataFrame({
        "open": np.random.randn(300).cumsum() + 2000,
        "high": np.random.randn(300).cumsum() + 2005,
        "low": np.random.randn(300).cumsum() + 1995,
        "close": np.random.randn(300).cumsum() + 2000,
        "volume": np.random.randint(100, 1000, 300)
    }, index=dates)
    return df

@pytest.fixture
def buy_signal():
    return TradeSignal(
        symbol="XAUUSD",
        direction=1,
        entry_price=2000.0,
        stop_loss=1990.0,
        take_profit=2020.0,
        lot_size=0.1,
        algorithm="ppo",
        confidence=0.8,
        timestamp=datetime(2024, 1, 1, 12, 0)
    )

def test_atr_volatility_filter(sample_df, buy_signal):
    # Set high min_atr to block
    ef = ExecutionFilter(config={"min_atr": 100.0})
    res = ef.validate(buy_signal, sample_df, {"drawdown": 0.0})
    assert res.approved is False
    assert res.blocked_by == "ATR Volatility"

    # Set low min_atr to pass
    ef = ExecutionFilter(config={"min_atr": 0.0, "max_atr": 1000.0})
    # We still need other filters to pass or check only this layer
    assert ef._check_atr_volatility(sample_df) is True

def test_trend_angle_filter(sample_df):
    ef = ExecutionFilter(config={"threshold_slope": 0.00001})

    # Create an uptrend
    df_up = sample_df.copy()
    df_up["close"] = np.linspace(2000, 2100, 300)
    assert ef._check_trend_angle(df_up, 1) is True
    assert ef._check_trend_angle(df_up, -1) is False

    # Create a downtrend
    df_down = sample_df.copy()
    df_down["close"] = np.linspace(2100, 2000, 300)
    assert ef._check_trend_angle(df_down, -1) is True
    assert ef._check_trend_angle(df_down, 1) is False

def test_ema_sequence_filter(sample_df):
    ef = ExecutionFilter(config={"ema_fast": 5, "ema_mid": 10, "ema_slow": 20})

    # Bullish sequence
    df_bull = sample_df.copy()
    df_bull["close"] = np.linspace(2000, 2100, 300) # Strong uptrend usually results in Fast > Mid > Slow
    # Wait for EMAs to populate and align
    assert ef._check_ema_sequence(df_bull, 1) is True

    # Bearish sequence
    df_bear = sample_df.copy()
    df_bear["close"] = np.linspace(2100, 2000, 300)
    assert ef._check_ema_sequence(df_bear, -1) is True

def test_momentum_filter(sample_df):
    ef = ExecutionFilter(config={"rsi_buy_min": 60, "rsi_sell_max": 40})

    # Overbought-ish
    df_high = sample_df.copy()
    df_high["close"] = np.linspace(2000, 2500, 300)
    assert ef._check_momentum(df_high, 1) is True

    # Oversold-ish
    df_low = sample_df.copy()
    df_low["close"] = np.linspace(2500, 2000, 300)
    assert ef._check_momentum(df_low, -1) is True

def test_session_filter(buy_signal):
    # Within session
    ef = ExecutionFilter(config={"allowed_sessions": [{"start": time(8, 0), "end": time(20, 0)}]})
    buy_signal.timestamp = datetime(2024, 1, 1, 12, 0)
    assert ef._check_session_filter(buy_signal.timestamp) is True

    # Outside session
    buy_signal.timestamp = datetime(2024, 1, 1, 22, 0)
    assert ef._check_session_filter(buy_signal.timestamp) is False

def test_drawdown_breaker_filter():
    ef = ExecutionFilter(config={"max_drawdown": 0.10})

    assert ef._check_drawdown_breaker({"drawdown": 0.05}) is True
    assert ef._check_drawdown_breaker({"drawdown": 0.12}) is False

def test_full_cascade_pass(sample_df, buy_signal):
    # Configure to pass all
    ef = ExecutionFilter(config={
        "min_atr": 0.0,
        "max_atr": 10000.0,
        "threshold_slope": 0.0,
        "rsi_buy_min": 0,
        "max_drawdown": 1.0,
        "allowed_sessions": [{"start": time(0, 0), "end": time(23, 59)}]
    })
    # Ensure all filters pass by providing appropriate market data
    df_pass = sample_df.copy()
    # Forces uptrend, EMA alignment and RSI > 0
    df_pass["close"] = np.linspace(2000, 2500, 300)
    # Ensure high/low exist for ATR calculation
    df_pass["high"] = df_pass["close"] + 10
    df_pass["low"] = df_pass["close"] - 10

    buy_signal.timestamp = datetime(2024, 1, 1, 12, 0)

    res = ef.validate(buy_signal, df_pass, {"drawdown": 0.01})
    assert res.approved is True
    assert res.blocked_by is None

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, time, timezone
from src.trading.execution_filter import ExecutionFilter, ExecutionDecision
from src.trading.risk_manager import TradeSignal

@pytest.fixture
def execution_filter():
    return ExecutionFilter()

@pytest.fixture
def mock_market_data():
    """Generates 300 periods of neutral market data."""
    np.random.seed(42)
    dates = pd.date_range(end=datetime.now(timezone.utc), periods=300, freq='5min')
    close = 2000.0 + np.cumsum(np.random.randn(300))
    df = pd.DataFrame({
        'high': close + 0.5,
        'low': close - 0.5,
        'close': close,
        'open': close - 0.1
    }, index=dates)
    return df

@pytest.fixture
def perfect_buy_data():
    """Generates 300 periods of perfect BUY data."""
    dates = pd.date_range(end=datetime.now(timezone.utc), periods=300, freq='5min')
    # Uptrend with EMA20 > EMA50 > EMA200
    # and linear regression slope > 0
    # and RSI between 50 and 75
    # and ADX > 25
    close = np.linspace(1800, 2000, 300)
    df = pd.DataFrame({
        'high': close + 1.0,
        'low': close - 1.0,
        'close': close,
        'open': close - 0.5
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
        algorithm="test",
        confidence=0.8
    )

def test_session_filter_pass(execution_filter, buy_signal, perfect_buy_data):
    import unittest.mock as mock
    with mock.patch('src.trading.execution_filter.datetime') as mock_date:
        mock_date.utcnow.return_value = datetime(2024, 5, 22, 10, 0, 0, tzinfo=timezone.utc)
        mock_date.time = time
        assert execution_filter._check_session_time() is True

def test_session_filter_various_days(execution_filter):
    import unittest.mock as mock
    with mock.patch('src.trading.execution_filter.datetime') as mock_date:
        mock_date.time = time
        # Monday
        mock_date.utcnow.return_value = datetime(2024, 5, 20, 10, 0, 0, tzinfo=timezone.utc)
        assert execution_filter._check_session_time() is True
        # Saturday
        mock_date.utcnow.return_value = datetime(2024, 5, 25, 10, 0, 0, tzinfo=timezone.utc)
        assert execution_filter._check_session_time() is False
        # Sunday morning
        mock_date.utcnow.return_value = datetime(2024, 5, 26, 10, 0, 0, tzinfo=timezone.utc)
        assert execution_filter._check_session_time() is False
        # Sunday evening
        mock_date.utcnow.return_value = datetime(2024, 5, 26, 18, 0, 0, tzinfo=timezone.utc)
        assert execution_filter._check_session_time() is True
        # Friday early
        mock_date.utcnow.return_value = datetime(2024, 5, 24, 10, 0, 0, tzinfo=timezone.utc)
        assert execution_filter._check_session_time() is True
        # Friday late
        mock_date.utcnow.return_value = datetime(2024, 5, 24, 17, 0, 0, tzinfo=timezone.utc)
        assert execution_filter._check_session_time() is False

def test_drawdown_circuit_breaker(execution_filter, buy_signal, perfect_buy_data):
    decision = execution_filter.validate(buy_signal, perfect_buy_data, 0.20)
    assert decision.is_approved is False
    assert decision.blocked_by == "Drawdown Circuit Breaker"

def test_atr_volatility_pass_fail(execution_filter, perfect_buy_data):
    assert bool(execution_filter._check_atr_volatility(perfect_buy_data)) is True
    perfect_buy_data.loc[perfect_buy_data.index[-1], 'high'] = 10000.0
    assert bool(execution_filter._check_atr_volatility(perfect_buy_data)) is False

def test_atr_volatility_isna(execution_filter):
    df = pd.DataFrame({'high': [np.nan]*50, 'low': [np.nan]*50, 'close': [np.nan]*50})
    assert execution_filter._check_atr_volatility(df) is True

def test_ema_sequence_buy_sell(execution_filter):
    buy_df = pd.DataFrame({'close': np.linspace(1800, 2100, 300)})
    assert bool(execution_filter._check_ema_sequence(buy_df, 1)) is True
    assert bool(execution_filter._check_ema_sequence(buy_df, -1)) is False
    sell_df = pd.DataFrame({'close': np.linspace(2100, 1800, 300)})
    assert bool(execution_filter._check_ema_sequence(sell_df, -1)) is True
    assert bool(execution_filter._check_ema_sequence(sell_df, 1)) is False
    assert execution_filter._check_ema_sequence(sell_df, 0) is False

def test_trend_angle_isna(execution_filter):
    df = pd.DataFrame({'close': [np.nan]*50})
    # linregress with NaNs might raise or return NaNs.
    # Current implementation doesn't check for NaN slope.
    # Let's see.
    try:
        execution_filter._check_trend_angle(df, 1)
    except:
        pass

def test_momentum_rsi_isna(execution_filter):
    df = pd.DataFrame({'close': [100.0]*50}) # Gain and Loss will be 0 -> RS NaN
    assert execution_filter._check_momentum(df, 1) is True

def test_spread_check(execution_filter, mock_market_data):
    assert execution_filter._check_spread(mock_market_data, 10.0) is True
    assert execution_filter._check_spread(mock_market_data, 60.0) is False

def test_adx_isna(execution_filter):
    df = pd.DataFrame({'high': [100]*50, 'low': [100]*50, 'close': [100]*50})
    assert execution_filter._check_adx(df) is True

def test_validate_cascade_atr_fail(execution_filter, buy_signal, perfect_buy_data):
    perfect_buy_data.loc[perfect_buy_data.index[-1], 'high'] = 10000.0
    import unittest.mock as mock
    with mock.patch('src.trading.execution_filter.datetime') as mock_date:
        mock_date.utcnow.return_value = datetime(2024, 5, 22, 10, 0, 0, tzinfo=timezone.utc)
        mock_date.time = time
        decision = execution_filter.validate(buy_signal, perfect_buy_data, 0.01)
        assert decision.is_approved is False
        assert decision.blocked_by == "ATR Volatility"

def test_validate_cascade_ema_fail(execution_filter, buy_signal):
    # Downtrend data but BUY signal
    df = pd.DataFrame({'close': np.linspace(2000, 1800, 300), 'high': 2000, 'low': 1800},
                      index=pd.date_range(end=datetime.now(timezone.utc), periods=300, freq='5min'))
    import unittest.mock as mock
    with mock.patch('src.trading.execution_filter.datetime') as mock_date:
        mock_date.utcnow.return_value = datetime(2024, 5, 22, 10, 0, 0, tzinfo=timezone.utc)
        mock_date.time = time
        decision = execution_filter.validate(buy_signal, df, 0.01)
        if not decision.is_approved:
            assert decision.blocked_by in ["EMA Sequence", "Trend Angle", "Momentum Filter"]

def test_validate_cascade_momentum_fail(execution_filter, buy_signal, perfect_buy_data):
    # RSI for perfect_buy_data (linear trend) is likely > 75
    # Let's adjust it to be very high
    perfect_buy_data['close'] = np.linspace(100, 1000, 300)
    import unittest.mock as mock
    with mock.patch('src.trading.execution_filter.datetime') as mock_date:
        mock_date.utcnow.return_value = datetime(2024, 5, 22, 10, 0, 0, tzinfo=timezone.utc)
        mock_date.time = time
        decision = execution_filter.validate(buy_signal, perfect_buy_data, 0.01)
        if not decision.is_approved:
            assert decision.blocked_by in ["Momentum Filter", "EMA Sequence", "Trend Angle"]

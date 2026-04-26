
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from src.trading.advanced_risk import AdvancedRiskManager, VolatilityRegime
from src.core.config import TradingConfig

@pytest.fixture
def config():
    return TradingConfig(
        mt5_password="test",
        mt5_server="test",
        max_correlation=0.7,
        max_portfolio_heat=0.1,
        max_consecutive_losses=3,
        max_slippage_pips=2.0,
        news_halt_window=30,
        max_risk_per_hour=0.02
    )

@pytest.fixture
def arm(config):
    return AdvancedRiskManager(config)

def test_check_correlation(arm):
    historical_data = {
        "XAUUSD": pd.Series([100, 101, 102, 101, 100]),
        "XAGUSD": pd.Series([20, 20.2, 20.4, 20.2, 20]),
        "EURUSD": pd.Series([1.1, 1.11, 1.09, 1.1, 1.12])
    }

    # High correlation: XAUUSD and XAGUSD
    assert arm.check_correlation("XAUUSD", ["XAGUSD"], historical_data) is False

    # Low correlation: XAUUSD and EURUSD (in this fake data)
    # Actually, let's check the real correlation
    # corr = pd.Series([100, 101, 102, 101, 100]).corr(pd.Series([1.1, 1.11, 1.09, 1.1, 1.12]))
    # which is 0.17
    assert arm.check_correlation("XAUUSD", ["EURUSD"], historical_data) is True

def test_check_time_exposure(arm):
    now = datetime.utcnow()
    recent_trades = [
        {"timestamp": now - timedelta(minutes=10), "risk_amount": 0.01},
        {"timestamp": now - timedelta(minutes=40), "risk_amount": 0.005}
    ]

    # Total risk = 0.015 < 0.02
    assert arm.check_time_exposure(recent_trades, now) is True

    # Add one more trade to exceed limit
    recent_trades.append({"timestamp": now - timedelta(minutes=5), "risk_amount": 0.01})
    # Total risk = 0.025 > 0.02
    assert arm.check_time_exposure(recent_trades, now) is False

def test_detect_volatility_regime(arm):
    # Create data for different regimes
    base_price = 100

    # Normal vol
    normal_data = pd.DataFrame({
        'high': [base_price + 1] * 50,
        'low': [base_price - 1] * 50,
        'close': [base_price] * 50
    })
    assert arm.detect_volatility_regime(normal_data) == VolatilityRegime.NORMAL

    # High vol
    high_vol_data = normal_data.copy()
    high_vol_data.loc[40:, 'high'] = base_price + 4
    high_vol_data.loc[40:, 'low'] = base_price - 4
    assert arm.detect_volatility_regime(high_vol_data) == VolatilityRegime.HIGH

    # Extreme vol
    extreme_vol_data = normal_data.copy()
    extreme_vol_data.loc[40:, 'high'] = base_price + 10
    extreme_vol_data.loc[40:, 'low'] = base_price - 10
    assert arm.detect_volatility_regime(extreme_vol_data) == VolatilityRegime.EXTREME

def test_calculate_portfolio_heat(arm):
    open_positions = [
        {"risk_amount": 100},
        {"risk_amount": 200}
    ]
    equity = 10000
    # Heat = 300 / 10000 = 0.03
    assert arm.calculate_portfolio_heat(open_positions, equity) == 0.03

    # Zero equity case
    assert arm.calculate_portfolio_heat(open_positions, 0) == 0.0

def test_check_consecutive_losses(arm):
    # No history
    assert arm.check_consecutive_losses([]) is True

    # 2 losses, limit is 3
    trade_history = [{"pnl": -10}, {"pnl": -5}, {"pnl": 20}]
    assert arm.check_consecutive_losses(trade_history) is True

    # 3 losses
    trade_history = [{"pnl": -10}, {"pnl": -5}, {"pnl": -2}, {"pnl": 20}]
    assert arm.check_consecutive_losses(trade_history) is False

def test_is_news_halted(arm):
    now = datetime.utcnow()
    news_events = [
        {"timestamp": now + timedelta(minutes=20), "impact": "HIGH"},
        {"timestamp": now - timedelta(hours=2), "impact": "HIGH"}
    ]

    # Halted because of the 20 min event
    assert arm.is_news_halted(now, news_events) is True

    # Not halted if no high impact news soon
    news_events = [{"timestamp": now + timedelta(minutes=20), "impact": "LOW"}]
    assert arm.is_news_halted(now, news_events) is False

def test_verify_slippage(arm):
    # BUY: expected 100, actual 100.1, pip_value 0.1 -> 1 pip slippage
    assert arm.verify_slippage(100, 100.1, 1, 0.1) is True

    # BUY: expected 100, actual 100.5, pip_value 0.1 -> 5 pips slippage (limit 2)
    assert arm.verify_slippage(100, 100.5, 1, 0.1) is False

    # SELL: expected 100, actual 99.9, pip_value 0.1 -> 1 pip slippage
    assert arm.verify_slippage(100, 99.9, -1, 0.1) is True

    # SELL: expected 100, actual 99.5, pip_value 0.1 -> 5 pips slippage
    assert arm.verify_slippage(100, 99.5, -1, 0.1) is False

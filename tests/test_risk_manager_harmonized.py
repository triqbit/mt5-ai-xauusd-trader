"""
Unified risk management harmonization tests.
Verifies the 8-layer safety cascade and ATR-based position sizing.
"""

from unittest.mock import MagicMock

import pandas as pd
import pytest

from src.core.config import TradingConfig
from src.core.schemas import SignalDirection, TradeSignal
from src.trading.risk_manager import RiskManager


@pytest.fixture
def mock_config():
    cfg = MagicMock(spec=TradingConfig)
    cfg.symbol = "XAUUSD"
    cfg.risk_per_trade = 0.01
    cfg.max_daily_loss = 0.05
    cfg.max_positions = 5
    cfg.min_confidence = 0.55
    cfg.min_lot_size = 0.01
    cfg.max_position_size_pct = 2.0  # 200% max position notional
    cfg.max_trades_per_day = 20
    cfg.max_losing_streak = 3
    cfg.model_drift_threshold = 0.3
    cfg.model_accuracy_floor = 0.5
    cfg.model_calibration_threshold = 0.25
    return cfg

@pytest.fixture
def market_data():
    # Create 100 bars of dummy data
    df = pd.DataFrame({
        "close": [2300.0] * 100,
        "high": [2305.0] * 100,
        "low": [2295.0] * 100,
        "atr": [10.0] * 100
    })
    return df

def test_risk_manager_approval_flow(mock_config, market_data):
    rm = RiskManager(mock_config, account_balance=1000000.0)

    signal = TradeSignal(
        symbol="XAUUSD",
        direction=SignalDirection.BUY,
        entry_price=2300.0,
        stop_loss=2280.0,
        take_profit=2340.0,
        lot_size=0.1,
        algorithm="test",
        confidence=0.7
    )

    decision = rm.approve(signal, market_data=market_data, open_positions=[])

    assert decision.is_approved is True
    assert decision.adjusted_lot_size > 0
    assert decision.trace["circuit_breaker"] is True

def test_daily_loss_cascading(mock_config, market_data):
    rm = RiskManager(mock_config, account_balance=1000000.0)

    # Simulate 3% loss (Level 2)
    rm.daily.realised_pnl = -30000.0
    rm.daily.peak_equity = 1000000.0

    signal = TradeSignal(
        symbol="XAUUSD",
        direction=SignalDirection.BUY,
        entry_price=2300.0,
        stop_loss=2280.0,
        take_profit=2340.0,
        lot_size=0.1,
        algorithm="test",
        confidence=0.7
    )

    decision = rm.approve(signal, market_data=market_data, open_positions=[])
    assert decision.is_approved is True
    # Balance 1M, Risk 1% = 10,000.
    # ATR 10 -> 1000$ per lot.
    # Normal sizing = 10,000 / 1000 = 10.0 lot.
    # Level 2 (3% loss) should reduce it by 50% -> 5.0 lot.
    assert decision.adjusted_lot_size == 5.0

    # Simulate 5% loss (Level 4 - Hard Halt)
    rm.daily.realised_pnl = -50000.0
    decision = rm.approve(signal, market_data=market_data, open_positions=[])
    assert decision.is_approved is False
    assert decision.reason == "daily_loss"

def test_exposure_limits(mock_config, market_data):
    rm = RiskManager(mock_config, account_balance=10000.0)

    # Simulate 5 open positions (Limit reached)
    open_positions = [{"ticket": i, "volume": 0.1, "type": 0} for i in range(5)]

    signal = TradeSignal(
        symbol="XAUUSD",
        direction=SignalDirection.BUY,
        entry_price=2300.0,
        stop_loss=2280.0,
        take_profit=2340.0,
        lot_size=0.1,
        algorithm="test",
        confidence=0.7
    )

    decision = rm.approve(signal, market_data=market_data, open_positions=open_positions)
    assert decision.is_approved is False
    assert decision.reason == "exposure_limits"

"""
Tests for the harmonized RiskManager architecture.
Verifies the 8-layer cascade and ATR-based sizing.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, UTC
from src.trading.risk_manager import RiskManager
from src.core.config import TradingConfig
from src.core.schemas import TradeSignal, RiskDecision

@pytest.fixture
def config():
    cfg = TradingConfig(
        MT5_PASSWORD="test",
        MT5_SERVER="test"
    )
    cfg.min_confidence = 0.55
    cfg.max_daily_loss = 0.05
    cfg.max_positions = 5
    cfg.risk_per_trade = 0.01
    return cfg

@pytest.fixture
def market_data():
    """Create synthetic market data with ATR."""
    df = pd.DataFrame({
        "close": [2300.0] * 100,
        "high": [2305.0] * 100,
        "low": [2295.0] * 100,
        "atr": [5.0] * 100
    })
    return df

@pytest.fixture
def risk_manager(config):
    return RiskManager(config, account_balance=10000.0)

def test_approve_valid_signal(risk_manager, market_data):
    signal = TradeSignal(
        symbol="XAUUSD",
        direction=1,
        entry_price=2300.0,
        stop_loss=2290.0,
        take_profit=2320.0,
        lot_size=0.1,
        algorithm="test",
        confidence=0.8
    )

    decision = risk_manager.approve(signal, market_data, open_positions=[])

    assert isinstance(decision, RiskDecision)
    assert decision.is_approved is True
    assert decision.adjusted_lot_size > 0
    assert decision.trace["circuit_breaker"] is True

def test_reject_low_confidence(risk_manager, market_data):
    signal = TradeSignal(
        symbol="XAUUSD",
        direction=1,
        entry_price=2300.0,
        stop_loss=2290.0,
        take_profit=2320.0,
        lot_size=0.1,
        algorithm="test",
        confidence=0.4  # Below 0.55
    )

    decision = risk_manager.approve(signal, market_data, open_positions=[])

    assert decision.is_approved is False
    assert "Confidence 0.40 below 0.55" in decision.reason
    assert decision.trace["min_confidence"] is False

def test_reject_max_positions(risk_manager, market_data):
    signal = TradeSignal(
        symbol="XAUUSD",
        direction=1,
        entry_price=2300.0,
        stop_loss=2290.0,
        take_profit=2320.0,
        lot_size=0.1,
        algorithm="test",
        confidence=0.8
    )

    # 5 positions already open
    open_positions = [{"ticket": i} for i in range(5)]

    decision = risk_manager.approve(signal, market_data, open_positions=open_positions)

    assert decision.is_approved is False
    assert "Max concurrent positions reached" in decision.reason

def test_atr_position_sizing(risk_manager, market_data):
    # Higher volatility (ATR = 16, while average is 5)
    high_vol_data = market_data.copy()
    high_vol_data.loc[high_vol_data.index[-1], "atr"] = 16.0

    lots = risk_manager.calculate_position_size("XAUUSD", high_vol_data)

    # Normal volatility sizing
    normal_lots = risk_manager.calculate_position_size("XAUUSD", market_data)

    # 15/5 = 3.0 ratio -> Extreme volatility -> should return 0.0 lots
    assert lots == 0.0
    assert normal_lots > 0.0

def test_daily_loss_circuit_breaker(risk_manager, market_data):
    # Simulate a loss
    risk_manager.record_pnl(-600.0) # 6% loss, exceeds 5% limit

    signal = TradeSignal(
        symbol="XAUUSD",
        direction=1,
        entry_price=2300.0,
        stop_loss=2290.0,
        take_profit=2320.0,
        lot_size=0.1,
        algorithm="test",
        confidence=0.8
    )

    decision = risk_manager.approve(signal, market_data, open_positions=[])
    assert decision.is_approved is False
    assert "Daily loss limit reached" in decision.reason

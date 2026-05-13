"""
Tests for the harmonized RiskManager.
Ensures that the new interface and logic (ATR sizing, exposure limits) are correct.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, UTC
from src.trading.risk_manager import RiskManager
from src.core.config import TradingConfig
from src.core.schemas import TradeSignal, SignalDirection

@pytest.fixture
def config():
    return TradingConfig(
        symbol="XAUUSD",
        risk_per_trade=0.01,
        max_positions=5,
        min_confidence=0.55,
        max_single_direction_pct=0.30,
        max_total_notional_pct=1.00,
        volatility_high_threshold=1.5,
        volatility_very_high_threshold=2.0,
        volatility_extreme_threshold=3.0,
        MT5_PASSWORD="fake",
        MT5_SERVER="fake",
        database_url="sqlite:///test.db"
    )

@pytest.fixture
def risk_manager(config):
    return RiskManager(config=config, account_balance=100000.0)

@pytest.fixture
def market_data():
    """Create sample market data with ATR."""
    data = {
        "time": pd.date_range(end=datetime.now(UTC), periods=1000, freq="5min"),
        "close": [2350.0] * 1000,
        "atr": [1.0] * 1000
    }
    return pd.DataFrame(data)

def test_risk_manager_approve_basic(risk_manager, market_data):
    """Test basic approval of a valid signal."""
    signal = TradeSignal(
        symbol="XAUUSD",
        direction=SignalDirection.BUY,
        entry_price=2350.0,
        stop_loss=2340.0,
        take_profit=2370.0,
        lot_size=0.1,
        algorithm="test",
        confidence=0.8
    )

    decision = risk_manager.approve(
        signal=signal,
        market_data=market_data,
        open_positions=[]
    )

    assert decision.is_approved is True
    assert decision.reason == "Approved"
    assert decision.adjusted_lot_size > 0

def test_risk_manager_reject_confidence(risk_manager, market_data):
    """Test rejection due to low confidence."""
    signal = TradeSignal(
        symbol="XAUUSD",
        direction=SignalDirection.BUY,
        entry_price=2350.0,
        stop_loss=2340.0,
        take_profit=2370.0,
        lot_size=0.1,
        algorithm="test",
        confidence=0.4 # Below 0.55
    )

    decision = risk_manager.approve(
        signal=signal,
        market_data=market_data,
        open_positions=[]
    )

    assert decision.is_approved is False
    assert "min_confidence" in decision.reason

def test_risk_manager_atr_scaling(risk_manager, market_data):
    """Test that lot size is reduced during high volatility."""
    signal = TradeSignal(
        symbol="XAUUSD",
        direction=SignalDirection.BUY,
        entry_price=2350.0,
        stop_loss=2340.0,
        take_profit=2370.0,
        lot_size=0.1,
        algorithm="test",
        confidence=0.8
    )

    # Use a specific risk amount that won't be capped by notional limits
    risk_manager.cfg.risk_per_trade = 0.0001 # 0.01%
    risk_manager.balance = 1000000.0
    risk_manager.peak_equity = 1000000.0
    risk_manager.daily.peak_equity = 1000000.0

    # Normal volatility (ATR=1.0, Average ATR=1.0)
    # Ratio = 1.0. multiplier = 1.0.
    # risk_amount = 100. lot_size = 100 / (1.0 * 100) = 1.0 lot.

    # Set max_position_size_pct high for test
    risk_manager.cfg.max_position_size_pct = 1.0

    decision_normal = risk_manager.approve(signal, market_data, [])

    # Very high volatility (Ratio 2.1 -> 50% size)
    vhigh_vol_data = market_data.copy()
    vhigh_vol_data.loc[vhigh_vol_data.index[-1], "atr"] = 2.1
    decision_vhigh = risk_manager.approve(signal, vhigh_vol_data, [])

    assert decision_vhigh.is_approved is True
    assert decision_vhigh.adjusted_lot_size < decision_normal.adjusted_lot_size

def test_risk_manager_exposure_limits(risk_manager, market_data):
    """Test directional and total notional exposure limits."""
    signal = TradeSignal(
        symbol="XAUUSD",
        direction=SignalDirection.BUY,
        entry_price=2350.0,
        stop_loss=2340.0,
        take_profit=2370.0,
        lot_size=0.1,
        algorithm="test",
        confidence=0.8
    )

    # Balance = 100,000. Max 30% = 30,000.
    # 1 lot = 235,000 notional.
    # 0.1 lot = 23,500. (Fits)

    decision_ok = risk_manager.approve(signal, market_data, [])
    assert decision_ok.is_approved is True

    # Now add existing positions to hit the 30% limit
    # 30,000 / 235,000 = ~0.127 lots
    open_positions = [
        {"symbol": "XAUUSD", "volume": 0.12, "type": 0} # BUY
    ]
    # 0.12 + 0.01 (min_lot) = 0.13
    # 0.13 * 235,000 = 30,550 (Slightly over 30,000)

    decision_too_much = risk_manager.approve(signal, market_data, open_positions)
    assert decision_too_much.is_approved is False
    assert "exposure_limits" in decision_too_much.reason

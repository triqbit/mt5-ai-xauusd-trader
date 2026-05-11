"""
Tests for the harmonized RiskManager.
Verifies the 8-layer cascade and institutional risk logic.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import date, datetime, UTC
from unittest.mock import MagicMock

from src.core.config import TradingConfig
from src.core.schemas import TradeSignal, RiskDecision
from src.trading.risk_manager import RiskManager

@pytest.fixture
def mock_cfg():
    cfg = MagicMock(spec=TradingConfig)
    cfg.symbol = "XAUUSD"
    cfg.risk_per_trade = 0.01
    cfg.max_daily_loss = 0.05
    cfg.max_positions = 5
    cfg.max_losing_streak = 3
    cfg.min_confidence = 0.55
    cfg.min_lot_size = 0.01
    cfg.model_drift_threshold = 0.3
    cfg.model_accuracy_floor = 0.5
    cfg.model_calibration_threshold = 0.1
    cfg.max_trades_per_day = 50
    # Add new institutional config attributes
    cfg.max_single_direction_pct = 0.30
    cfg.max_total_notional_pct = 10.0
    return cfg

@pytest.fixture
def market_data():
    data = {
        "close": [2300.0] * 20,
        "high": [2305.0] * 20,
        "low": [2295.0] * 20,
        "atr": [5.0] * 20
    }
    return pd.DataFrame(data)

@pytest.fixture
def trade_signal():
    return TradeSignal(
        symbol="XAUUSD",
        direction=1,
        entry_price=2300.0,
        stop_loss=2290.0,
        take_profit=2320.0,
        lot_size=0.01,
        algorithm="test",
        confidence=0.8,
        timestamp=datetime.now(UTC)
    )

def test_risk_manager_approval_flow(mock_cfg, market_data, trade_signal):
    rm = RiskManager(mock_cfg, account_balance=10000.0)
    # Ensure no clashing from default weights in test env
    from src.trading.risk_manager import ALLOCATION_WEIGHTS
    ALLOCATION_WEIGHTS["XAUUSD"] = 0.18

    decision = rm.approve(
        signal=trade_signal,
        market_data=market_data,
        open_positions=[]
    )

    assert isinstance(decision, RiskDecision)
    assert decision.is_approved is True
    assert decision.adjusted_lot_size >= mock_cfg.min_lot_size
    assert len(decision.trace) == 8

def test_risk_manager_circuit_breaker(mock_cfg, market_data, trade_signal):
    rm = RiskManager(mock_cfg, account_balance=8000.0) # 20% drawdown from 10000 peak
    rm.peak_equity = 10000.0

    decision = rm.approve(
        signal=trade_signal,
        market_data=market_data,
        open_positions=[]
    )

    assert decision.is_approved is False
    assert decision.trace["layer1_drawdown"] is False

def test_risk_manager_daily_loss_limit(mock_cfg, market_data, trade_signal):
    rm = RiskManager(mock_cfg, account_balance=10000.0)
    rm.daily.realised_pnl = -600.0 # 6% loss
    rm.daily.peak_equity = 10000.0

    decision = rm.approve(
        signal=trade_signal,
        market_data=market_data,
        open_positions=[]
    )

    assert decision.is_approved is False
    assert decision.trace["layer2_daily_loss"] is False

def test_risk_manager_max_positions(mock_cfg, market_data, trade_signal):
    rm = RiskManager(mock_cfg, account_balance=10000.0)
    open_positions = [{"ticket": i, "volume": 0.1, "type": 0} for i in range(5)]

    decision = rm.approve(
        signal=trade_signal,
        market_data=market_data,
        open_positions=open_positions
    )

    assert decision.is_approved is False
    assert decision.trace["layer4_exposure"] is False

def test_risk_manager_directional_exposure(mock_cfg, market_data, trade_signal):
    rm = RiskManager(mock_cfg, account_balance=10000.0)
    # Huge position to trigger 30% cap
    open_positions = [{"ticket": 1, "volume": 20.0, "type": 0}]

    decision = rm.approve(
        signal=trade_signal,
        market_data=market_data,
        open_positions=open_positions
    )

    assert decision.is_approved is False
    assert decision.trace["layer4_exposure"] is False

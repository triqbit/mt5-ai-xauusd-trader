"""
MT5 AI/ML Trading Bot - Enterprise Edition
tests/test_risk_engine_new.py
Unified verification of harmonized Risk Management logic.
"""

import os

import pandas as pd
import pytest

from src.core.config import TradingConfig
from src.core.schemas import SignalDirection, TradeSignal
from src.trading.risk_manager import RiskManager


@pytest.fixture
def config():
    os.environ["MT5_PASSWORD"] = "dummy"
    os.environ["MT5_SERVER"] = "dummy"
    return TradingConfig(
        symbol="XAUUSD",
        risk_per_trade=0.01,
        max_daily_loss=0.05,
        max_positions=3,
        max_trades_per_day=10,
        max_losing_streak=5,
        min_confidence=0.6,
        max_drawdown=0.15,
        max_single_direction_pct=0.3,
        max_total_notional_pct=1.0,
        min_lot_size=0.01,
        volatility_high_threshold=1.5,
        volatility_very_high_threshold=2.0,
        volatility_extreme_threshold=3.0,
        max_position_size_pct=0.1,
        model_drift_threshold=0.3,
        model_accuracy_floor=0.5,
        model_calibration_threshold=0.2,
    )

@pytest.fixture
def risk_manager(config):
    return RiskManager(config, 10000.0)

def test_circuit_breaker(risk_manager):
    # Layer 1: Drawdown
    risk_manager.peak_equity = 10000.0
    risk_manager.balance = 8000.0 # 20% drawdown > 15% limit

    # Simple signal
    sig = TradeSignal(
        symbol="XAUUSD", direction=SignalDirection.BUY, entry_price=2300,
        stop_loss=2290, take_profit=2320, lot_size=0.1, algorithm="test", confidence=0.8
    )
    # market_data
    df = pd.DataFrame({"atr": [1.0], "close": [2300.0]})

    res = risk_manager.validate_signal(sig, df, [])
    assert not res.is_approved
    assert "Circuit breaker" in res.reason

def test_daily_loss_limit(risk_manager):
    risk_manager.daily.realised_pnl = -600.0 # 6% loss > 5% limit
    sig = TradeSignal(
        symbol="XAUUSD", direction=SignalDirection.BUY, entry_price=2300,
        stop_loss=2290, take_profit=2320, lot_size=0.1, algorithm="test", confidence=0.8
    )
    df = pd.DataFrame({"atr": [1.0], "close": [2300.0]})
    res = risk_manager.validate_signal(sig, df, [])
    assert not res.is_approved
    assert "Daily loss limit" in res.reason

def test_directional_exposure(risk_manager):
    sig = TradeSignal(
        symbol="XAUUSD", direction=SignalDirection.BUY, entry_price=2300,
        stop_loss=2290, take_profit=2320, lot_size=0.1, algorithm="test", confidence=0.8
    )
    # Balance 10000, 30% limit = 3000
    # Gold 2300. 1 lot = 230000. 0.1 lot = 23000.
    # We need to hit > 3000. 0.02 lots is ~4600.
    open_positions = [{"symbol": "XAUUSD", "volume": 0.02, "type": 0}] # type 0 = BUY
    df = pd.DataFrame({"atr": [1.0], "close": [2300.0]})

    res = risk_manager.validate_signal(sig, df, open_positions)
    assert not res.is_approved
    assert "directional exposure" in res.reason.lower()

def test_model_health_gate(risk_manager):
    sig = TradeSignal(
        symbol="XAUUSD", direction=SignalDirection.BUY, entry_price=2300,
        stop_loss=2290, take_profit=2320, lot_size=0.1, algorithm="test", confidence=0.8
    )
    df = pd.DataFrame({"atr": [1.0], "close": [2300.0]})
    health = {"drift": 0.5} # > 0.3 threshold

    res = risk_manager.validate_signal(sig, df, [], model_health=health)
    assert not res.is_approved
    assert "Model health" in res.reason

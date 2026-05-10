"""
MT5 AI/ML Trading Bot - Enterprise Edition
tests/test_risk_manager_harmonized.py
Comprehensive tests for the unified RiskManager and AuditedRiskManager.
"""

from unittest.mock import MagicMock

import pandas as pd
import pytest

from src.core.config import TradingConfig
from src.core.constants import SignalDirection
from src.core.schemas import TradeSignal
from src.trading.risk_manager import RiskManager


@pytest.fixture
def risk_manager():
    cfg = TradingConfig(MT5_PASSWORD="test", MT5_SERVER="test")
    # Set standard thresholds for testing
    cfg.max_drawdown = 0.12
    cfg.max_daily_loss = 0.05
    cfg.max_trades_per_day = 10
    cfg.max_losing_streak = 5
    cfg.max_positions = 5
    cfg.min_confidence = 0.55
    cfg.min_lot_size = 0.01
    cfg.risk_per_trade = 0.01
    cfg.max_single_direction_pct = 0.30  # Default
    return RiskManager(cfg, 100000.0)  # Use 100k balance to make exposure checks easier


def test_drawdown_breaker(risk_manager):
    """Test Layer 1: Circuit Breakers (Equity Drawdown)."""
    risk_manager.update_equity(80000.0)  # 20% drawdown on 100k
    assert not risk_manager._check_drawdown_breaker()


def test_daily_loss_level(risk_manager):
    """Test Layer 2: Daily Loss Limits."""
    risk_manager.update_equity(100000.0, realized_pnl=-6000.0)  # 6% loss > 5% limit
    assert risk_manager.get_daily_loss_level() >= 4


def test_activity_limits(risk_manager):
    """Test Layer 3: Activity Limits."""
    risk_manager.daily.trade_count = 11  # > 10 limit
    signal = TradeSignal(
        symbol="XAUUSD",
        direction=SignalDirection.BUY,
        entry_price=2300.0,
        stop_loss=2290.0,
        take_profit=2320.0,
        lot_size=0.1,
        algorithm="ppo",
        confidence=0.7,
    )
    data = pd.DataFrame({"atr": [1.0], "close": [2300.0]})
    decision = risk_manager.approve(signal, data, [])
    assert not decision.is_approved
    assert "Max daily trades" in decision.reason
    assert decision.trace["max_trades"] is False


def test_exposure_limits(risk_manager):
    """Test Layer 4: Exposure Limits."""
    # Max positions
    open_positions = [{"volume": 0.1, "type": 0}] * 5
    signal = TradeSignal(
        symbol="XAUUSD",
        direction=SignalDirection.BUY,
        entry_price=2300.0,
        stop_loss=2290.0,
        take_profit=2320.0,
        lot_size=0.1,
        algorithm="ppo",
        confidence=0.7,
    )
    data = pd.DataFrame({"atr": [1.0], "close": [2300.0]})
    decision = risk_manager.approve(signal, data, open_positions)
    assert not decision.is_approved
    assert "Max concurrent positions" in decision.reason
    assert decision.trace["max_positions"] is False


def test_atr_position_sizing(risk_manager):
    """Test ATR-based position sizing logic."""
    # Normal volatility
    data = pd.DataFrame({"atr": [1.0] * 100, "close": [2300.0] * 100})
    size = risk_manager.calculate_position_size("XAUUSD", data)
    assert size >= 0.01

    # Very High volatility (> 2x normal)
    # average ATR will be 1.0. If we push ATR to 5.0, it is > 3.0x -> extreme -> 0.0 lots
    atr_values = [1.0] * 8640 + [5.0]
    data_extreme = pd.DataFrame({"atr": atr_values, "close": [2300.0] * 8641})
    size_extreme = risk_manager.calculate_position_size("XAUUSD", data_extreme)
    assert size_extreme == 0.0


def test_full_cascade_approval(risk_manager):
    """Test full 8-layer cascade for a valid signal."""
    signal = TradeSignal(
        symbol="XAUUSD",
        direction=SignalDirection.BUY,
        entry_price=2300.0,
        stop_loss=2290.0,
        take_profit=2320.0,
        lot_size=0.1,
        algorithm="ppo",
        confidence=0.8,
    )
    # Mock history to pass ATR sizing check
    atr_values = [1.0] * 8641
    data_hist = pd.DataFrame({"atr": atr_values, "close": [2300.0] * 8641})

    decision = risk_manager.approve(signal, data_hist, [])
    assert decision.is_approved, f"Failed: {decision.reason} | Trace: {decision.trace}"
    assert decision.reason == "Approved"
    assert decision.adjusted_lot_size >= 0.01
    assert all(decision.trace.values())

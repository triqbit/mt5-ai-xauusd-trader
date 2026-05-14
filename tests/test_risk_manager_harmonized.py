import pytest
import pandas as pd
from datetime import date
from src.trading.risk_manager import AuditedRiskManager
from src.core.schemas import TradeSignal
from src.core.constants import SignalDirection
from unittest.mock import MagicMock

@pytest.fixture
def mock_cfg():
    cfg = MagicMock()
    cfg.risk_per_trade = 0.01
    cfg.max_drawdown = 0.15
    cfg.max_daily_loss = 0.05
    cfg.max_positions = 5
    cfg.min_confidence = 0.55
    cfg.max_losing_streak = 3
    cfg.model_drift_threshold = 0.3
    cfg.model_accuracy_floor = 0.45
    cfg.model_calibration_threshold = 0.25
    cfg.min_lot_size = 0.01
    cfg.volatility_extreme_threshold = 3.0
    cfg.volatility_very_high_threshold = 2.0
    cfg.volatility_high_threshold = 1.5
    cfg.symbol = "XAUUSD"
    cfg.max_trades_per_day = 20
    cfg.daily_loss_lvl1 = 0.02
    cfg.daily_loss_lvl2 = 0.03
    cfg.daily_loss_lvl3 = 0.04
    cfg.max_position_size_pct = 5.0
    cfg.max_total_notional_pct = 10.0
    return cfg

@pytest.fixture
def risk_manager(mock_cfg):
    return AuditedRiskManager(mock_cfg, account_balance=10000.0)

def test_circuit_breaker(risk_manager):
    # Initial state
    assert risk_manager._check_drawdown_breaker() is True

    # 16% drawdown
    risk_manager.balance = 8400.0
    assert risk_manager._check_drawdown_breaker() is False

def test_daily_loss_limit(risk_manager):
    risk_manager.daily.realised_pnl = -501.0 # > 5% of 10000
    assert risk_manager.get_daily_loss_level() == 4

    signal = TradeSignal(
        symbol="XAUUSD",
        direction=SignalDirection.BUY,
        entry_price=2300.0,
        stop_loss=2290.0,
        take_profit=2320.0,
        lot_size=0.1,
        algorithm="test",
        confidence=0.7
    )
    decision = risk_manager.validate_signal(signal)
    assert decision.is_approved is False
    assert "daily_loss" in decision.trace
    assert decision.trace["daily_loss"] is False

def test_atr_position_sizing(risk_manager):
    # Normal volatility
    df = pd.DataFrame({
        "close": [2300.0] * 20,
        "atr": [10.0] * 20
    })

    lots = risk_manager.calculate_position_size("XAUUSD", df)
    # risk_amount = 100, atr=10.0 -> lots = 100 / (10 * 100) = 0.1
    assert lots == 0.1

    # High volatility
    df_high = pd.DataFrame({
        "close": [2300.0] * 100,
        "atr": [10.0] * 80 + [20.0] * 20
    })
    lots_high = risk_manager.calculate_position_size("XAUUSD", df_high)
    # If window is all data, avg_atr = (80*10 + 20*20)/100 = 12.0
    # ratio = 20 / 12 = 1.66 -> High volatility (>1.5) -> 75% sizing
    # base lots = 100 / (20 * 100) = 0.05. 75% of 0.05 = 0.0375 -> 0.04
    assert lots_high == 0.04

def test_validate_signal_full_cascade(risk_manager):
    signal = TradeSignal(
        symbol="XAUUSD",
        direction=SignalDirection.BUY,
        entry_price=2300.0,
        stop_loss=2290.0,
        take_profit=2320.0,
        lot_size=0.1,
        algorithm="test",
        confidence=0.7
    )

    df = pd.DataFrame({"close": [2300.0] * 20, "atr": [10.0] * 20})

    decision = risk_manager.validate_signal(signal, market_data=df)
    assert decision.is_approved is True
    assert decision.adjusted_lot_size == 0.1
    assert all(decision.trace.values())

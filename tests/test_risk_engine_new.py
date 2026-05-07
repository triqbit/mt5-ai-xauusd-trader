"""Tests for src.trading.risk_engine module."""
import pytest
import pandas as pd
from src.trading.risk_engine import RiskEngine
from src.core.config import TradingConfig
from src.core.schemas import TradeSignal
from src.core.constants import SignalDirection

@pytest.fixture
def risk_engine():
    # Force defaults that match our expectations
    cfg = TradingConfig(
        MT5_PASSWORD="test",
        MT5_SERVER="test",
        RISK_PER_TRADE=0.01,
        MIN_LOT_SIZE=0.01,
        MAX_POSITION_SIZE_PCT=0.5 # Increase for testing position sizing
    )
    return RiskEngine(cfg, 10000.0)

def test_drawdown_breaker(risk_engine):
    # 30% drawdown limit by default
    risk_engine.update_metrics(10000.0) # Peak
    risk_engine.update_metrics(6500.0)  # 35% drawdown
    assert not risk_engine._check_drawdown_breaker()

def test_daily_loss_breaker(risk_engine):
    # 5% max daily loss limit by default
    risk_engine.update_metrics(10000.0, realized_pnl=-600.0) # 6% loss
    assert risk_engine.get_daily_loss_level() >= 4

def test_calculate_position_size_normal(risk_engine):
    # XAUUSD: risk 1% of 10000 = 100. ATR 1.0.
    # Calculation: (100 / (1.0 * 100)) = 1.0 lot.
    # Price is 2300, so max_lots at 50% equity (5000) is 5000 / 230000 = 0.0217.
    # Wait, 1.0 lot is 100 ounces of gold. 1.0 * 2300 * 100 = 230,000 notional.
    # To have 1.0 lot as 50% of equity, equity must be 460,000.
    risk_engine.balance = 500000.0
    risk_engine.cfg.risk_per_trade = 0.01 # Risk 5000
    # ATR 10.0 -> 5000 / (10 * 100) = 5.0 lots
    # Max notional 50% of 500,000 = 250,000.
    # Price 2300 -> 250,000 / 230,000 = 1.08 lots max.

    data = pd.DataFrame({
        "atr": [1.0] * 9000,
        "close": [2300.0] * 9000
    })
    # Let's use simpler numbers.
    risk_engine.balance = 100000.0
    risk_engine.cfg.risk_per_trade = 0.01 # Risk 1000
    risk_engine.cfg.max_position_size_pct = 1.0 # 100%
    # ATR 1.0 -> 1000 / (1.0 * 100) = 10.0 lots
    # Max lots (100% of 100k) = 100,000 / (2300 * 100) = 0.434 lots.
    # Still small. Gold is expensive!

    # Let's use ATR that gives smaller lot size.
    # Risk 1000. ATR 50.0 -> 1000 / (50 * 100) = 0.2 lots.
    # Max lots (100% of 100k) = 0.434.
    # 0.2 < 0.434 so it should be 0.2.

    data = pd.DataFrame({
        "atr": [50.0] * 9000,
        "close": [2300.0] * 9000
    })
    size = risk_engine.calculate_position_size("XAUUSD", data)
    assert size == pytest.approx(0.2, 0.01)

def test_calculate_position_size_high_vol(risk_engine):
    risk_engine.balance = 100000.0
    risk_engine.cfg.risk_per_trade = 0.01 # Risk 1000
    risk_engine.cfg.max_position_size_pct = 1.0

    # Average ATR 50.0, current ATR 80.0 (1.6x average -> 75% sizing)
    # Risk 1000 / (80 * 100) = 0.125
    # 0.125 * 0.75 = 0.09375 -> 0.09 rounded
    atr_values = [50.0] * 8999 + [80.0]
    data = pd.DataFrame({
        "atr": atr_values,
        "close": [2300.0] * len(atr_values)
    })
    size = risk_engine.calculate_position_size("XAUUSD", data)
    assert size == pytest.approx(0.09, 0.01)

def test_validate_signal_approved(risk_engine):
    signal = TradeSignal(
        symbol="XAUUSD",
        direction=SignalDirection.BUY,
        entry_price=2300.0,
        stop_loss=2290.0,
        take_profit=2320.0,
        lot_size=0.1,
        algorithm="ppo",
        confidence=0.7
    )
    data = pd.DataFrame({"atr": [1.0] * 100, "close": [2300.0] * 100})
    decision = risk_engine.validate_signal(signal, data, [])
    assert decision.is_approved
    assert decision.adjusted_lot_size > 0

def test_validate_signal_rejection_confidence(risk_engine):
    signal = TradeSignal(
        symbol="XAUUSD",
        direction=SignalDirection.BUY,
        entry_price=2300.0,
        stop_loss=2290.0,
        take_profit=2320.0,
        lot_size=0.1,
        algorithm="ppo",
        confidence=0.54 # Below 0.55
    )
    data = pd.DataFrame({"atr": [1.0] * 100, "close": [2300.0] * 100})
    decision = risk_engine.validate_signal(signal, data, [])
    assert not decision.is_approved
    assert "Confidence" in decision.reason

"""Tests for src.trading.risk_engine module."""
import pytest
from unittest.mock import MagicMock
from src.trading.risk_engine import RiskEngine, TradeSignal
from src.core.config import TradingConfig

@pytest.fixture
def mock_config():
    cfg = MagicMock(spec=TradingConfig)
    cfg.risk_per_trade = 0.01
    cfg.max_positions = 5
    cfg.max_daily_trades = 20
    cfg.min_confidence = 0.55
    cfg.daily_loss_lvl2 = 0.03
    cfg.daily_loss_lvl3 = 0.04
    cfg.daily_loss_lvl4 = 0.05
    cfg.drawdown_lvl2 = 0.15
    cfg.drawdown_lvl3 = 0.20
    cfg.drawdown_lvl4 = 0.25
    cfg.drawdown_lvl5 = 0.30
    return cfg

def test_risk_engine_initialization(mock_config):
    engine = RiskEngine(mock_config, 10000.0)
    assert engine.balance == 10000.0
    assert engine.peak_equity == 10000.0

def test_approve_signal_success(mock_config):
    engine = RiskEngine(mock_config, 100000.0)
    signal = TradeSignal(
        symbol="XAUUSD",
        direction=1,
        entry_price=2000.0,
        stop_loss=1990.0,
        take_profit=2020.0,
        lot_size=0.01,
        algorithm="test",
        confidence=0.7
    )
    assert engine.approve(signal)

def test_approve_signal_low_confidence(mock_config):
    engine = RiskEngine(mock_config, 10000.0)
    signal = TradeSignal(
        symbol="XAUUSD",
        direction=1,
        entry_price=2000.0,
        stop_loss=1990.0,
        take_profit=2020.0,
        lot_size=0.01,
        algorithm="test",
        confidence=0.5 # < 0.55
    )
    assert not engine.approve(signal)

def test_calculate_position_size_normal(mock_config):
    # Balance $1M. 10% notional cap = $100,000.
    # Gold @ $2000, 100 contract size -> 1 lot = $200,000 notional.
    # So 0.5 lot = $100,000 notional (the cap).
    engine = RiskEngine(mock_config, 1000000.0)
    lot_size = engine.calculate_position_size(
        "XAUUSD", 2000.0, 1990.0, 1.0, 1.0
    )
    assert lot_size == 0.5

def test_daily_loss_cascading_limit(mock_config):
    engine = RiskEngine(mock_config, 1000000.0)
    engine.daily.peak_equity = 1000000.0

    # 4.5% loss triggers lvl3 (4%) -> 25% sizing
    engine.daily.realised_pnl = -45000.0

    # Entry 2000, Stop 1750 -> risk_per_lot = 250.
    # Gold contract size 100 -> $25,000 risk per lot.
    # Risk 1% of $1M = $10,000.
    # Normal lot size = 10,000 / 25,000 = 0.4 lots.
    # Notional of 0.4 lots = 0.4 * 100 * 2000 = $80,000 (below $100,000 cap).
    # With 25% multiplier: 0.4 * 0.25 = 0.1 lots.

    lot_size = engine.calculate_position_size("XAUUSD", 2000.0, 1750.0, 1.0, 1.0)
    assert lot_size == 0.1

def test_drawdown_circuit_breaker(mock_config):
    engine = RiskEngine(mock_config, 10000.0)
    engine.peak_equity = 15000.0
    # 33.3% drawdown > 30% (lvl5)

    signal = TradeSignal(
        symbol="XAUUSD", direction=1, entry_price=2000.0, stop_loss=1990.0,
        take_profit=2020.0, lot_size=0.01, algorithm="test", confidence=0.7
    )
    assert not engine.approve(signal)

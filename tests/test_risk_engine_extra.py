"""Additional tests for src.trading.risk_engine to improve coverage."""
import pytest
from unittest.mock import MagicMock
from src.trading.risk_engine import RiskEngine, TradeSignal, DailyRiskStats

@pytest.fixture
def mock_config():
    cfg = MagicMock()
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

def test_risk_per_trade_violation(mock_config):
    engine = RiskEngine(mock_config, 1000.0) # Balance 1000
    # Risk = (2000 - 1900) * 1.0 = 100 points
    # Points * contract size 100 = $10,000 risk.
    # $10,000 / 1000 = 1000% risk > 1% limit.
    signal = TradeSignal(
        symbol="XAUUSD", direction=1, entry_price=2000.0, stop_loss=1900.0,
        take_profit=2100.0, lot_size=1.0, algorithm="test", confidence=0.7
    )

    assert not engine.approve(signal)

def test_max_daily_trades_reached(mock_config):
    engine = RiskEngine(mock_config, 10000.0)
    engine.daily.trade_count = 20 # Limit is 20
    signal = TradeSignal(
        symbol="XAUUSD", direction=1, entry_price=2000.0, stop_loss=1990.0,
        take_profit=2010.0, lot_size=0.01, algorithm="test", confidence=0.7
    )
    assert not engine.approve(signal)

def test_consecutive_losses_halt(mock_config):
    engine = RiskEngine(mock_config, 10000.0)
    engine.daily.consecutive_losses = 3
    signal = TradeSignal(
        symbol="XAUUSD", direction=1, entry_price=2000.0, stop_loss=1990.0,
        take_profit=2010.0, lot_size=0.01, algorithm="test", confidence=0.7
    )
    assert not engine.approve(signal)

def test_max_positions_reached(mock_config):
    engine = RiskEngine(mock_config, 10000.0)
    engine.open_positions = {"S1": 1, "S2": 2, "S3": 3, "S4": 4, "S5": 5}
    signal = TradeSignal(
        symbol="XAUUSD", direction=1, entry_price=2000.0, stop_loss=1990.0,
        take_profit=2010.0, lot_size=0.01, algorithm="test", confidence=0.7
    )
    assert not engine.approve(signal)

def test_calculate_position_size_extreme_volatility(mock_config):
    engine = RiskEngine(mock_config, 10000.0)
    # ATR 4.0 vs Avg ATR 1.0 -> 4x normal -> Extreme -> 0 sizing
    lot_size = engine.calculate_position_size("XAUUSD", 2000.0, 1990.0, 4.0, 1.0)
    assert lot_size == 0.0

def test_record_trade_result(mock_config):
    engine = RiskEngine(mock_config, 10000.0)
    engine.record_trade_result(-100.0)
    assert engine.daily.realised_pnl == -100.0
    assert engine.daily.trade_count == 1
    assert engine.daily.consecutive_losses == 1

    engine.record_trade_result(200.0)
    assert engine.daily.realised_pnl == 100.0
    assert engine.daily.trade_count == 2
    assert engine.daily.consecutive_losses == 0

def test_reset_daily(mock_config):
    engine = RiskEngine(mock_config, 10000.0)
    engine.daily.realised_pnl = 500.0
    engine.daily.trade_count = 5

    engine.reset_daily()
    assert engine.daily.realised_pnl == 0.0
    assert engine.daily.trade_count == 0
    assert engine.daily.peak_equity == 10000.0

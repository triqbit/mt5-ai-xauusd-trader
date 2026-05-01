import pytest
from src.trading.risk_engine import RiskEngine
from src.trading.risk_manager import TradeSignal
from src.core.config import TradingConfig

@pytest.fixture
def risk_engine():
    cfg = TradingConfig(
        mt5_login=1, mt5_password="p", mt5_server="s",
        risk_per_trade=0.01,
        max_positions=3,
        min_confidence=0.55
    )
    return RiskEngine(cfg, account_balance=10000.0)

def test_validate_signal_approved(risk_engine):
    signal = TradeSignal(
        symbol="XAUUSD",
        direction=1,
        entry_price=2000.0,
        stop_loss=1990.0,
        take_profit=2020.0,
        lot_size=0.1,
        algorithm="ppo",
        confidence=0.7
    )
    decision = risk_engine.validate_signal(signal)
    assert decision.is_approved is True

def test_validate_signal_rejected_confidence(risk_engine):
    signal = TradeSignal(
        symbol="XAUUSD",
        direction=1,
        entry_price=2000.0,
        stop_loss=1990.0,
        take_profit=2020.0,
        lot_size=0.1,
        algorithm="ppo",
        confidence=0.5
    )
    decision = risk_engine.validate_signal(signal)
    assert decision.is_approved is False
    assert "Confidence" in decision.blocked_by

def test_drawdown_breaker(risk_engine):
    risk_engine.update_performance(-3500, 6500) # 35% drawdown
    signal = TradeSignal(
        symbol="XAUUSD", direction=1, entry_price=2000, stop_loss=1990,
        take_profit=2020, lot_size=0.1, algorithm="ppo", confidence=0.8
    )
    decision = risk_engine.validate_signal(signal)
    assert decision.is_approved is False
    assert "Drawdown" in decision.blocked_by

def test_calculate_lot_size(risk_engine):
    # Balance 1M, risk 1% = $10,000.
    # ATR = 50. Multiplier = 2.0. ContractSize = 100.
    # Sizing = 10000 / (50 * 2.0 * 100) = 10000 / 10000 = 1.0 lot.
    # Nominal = 1.0 * 2000 * 100 = 200,000.
    # 10% of 1M = 100,000. Nominal is too high!
    # Recalculated lot = 100,000 / (2000 * 100) = 0.5 lot.
    lot = risk_engine.calculate_lot_size("XAUUSD", 2000.0, 1900.0, 50.0, 1000000.0)
    assert lot == 0.5

def test_calculate_lot_size_small(risk_engine):
    # Balance 1M, risk 1% = $10,000.
    # ATR = 500. Multiplier = 2.0. ContractSize = 100.
    # Sizing = 10000 / (500 * 2.0 * 100) = 10000 / 100000 = 0.1 lot.
    # Nominal = 0.1 * 2000 * 100 = 20,000.
    # 10% of 1M = 100,000. Under limit!
    lot = risk_engine.calculate_lot_size("XAUUSD", 2000.0, 1900.0, 500.0, 1000000.0)
    assert lot == 0.1

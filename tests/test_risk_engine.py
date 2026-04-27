import pytest
from src.trading.risk_engine import RiskEngine
from src.core.config import TradingConfig

@pytest.fixture
def risk_engine():
    config = TradingConfig(mt5_password="test", mt5_server="test")
    engine = RiskEngine(config)
    engine.update_peak_equity(10000.0)
    return engine

def test_daily_loss_circuit_breaker(risk_engine):
    """Test cascading daily loss limits."""
    # 0.02 is lvl1 alert
    risk_engine.update_stats(-201.0, False) # > 2% of 10000
    res = risk_engine.check_signal("XAUUSD", 1, 0.7, 10000.0, 0)
    assert res["approved"] # Lvl 1 is just an alert, not a halt

    # 0.05 is lvl4 halt
    risk_engine.update_stats(-300.0, False) # Total -501.0 ( > 5% )
    res = risk_engine.check_signal("XAUUSD", 1, 0.7, 10000.0, 0)
    assert not res["approved"]
    assert "Daily Emergency Stop" in res["reason"]

def test_drawdown_circuit_breaker(risk_engine):
    """Test cascading drawdown limits."""
    # Initial equity 10000
    # Drop to 8400 (16% DD) -> lvl 2 (75% sizing)
    res = risk_engine.check_signal("XAUUSD", 1, 0.7, 8400.0, 0)
    assert res["approved"]

    # Drop to 7400 (26% DD) -> lvl 4 halt
    res = risk_engine.check_signal("XAUUSD", 1, 0.7, 7400.0, 0)
    assert not res["approved"]
    assert "drawdown Halt New Positions" in res["reason"]

def test_position_sizing_atr(risk_engine):
    """Test ATR-based position sizing calculation."""
    # current_equity = 10000, risk_per_trade = 0.01 ($100 risk)
    # sl_distance = 5.0 (e.g. 2350 to 2345)
    # lot_size = 100 / (5.0 * 100) = 0.2

    size = risk_engine.calculate_position_size(
        symbol="XAUUSD",
        entry_price=2350.0,
        stop_loss=2345.0,
        atr=2.0,
        current_equity=10000.0,
        confidence=0.7
    )
    assert size == 0.2

def test_position_sizing_confidence_scaling(risk_engine):
    """Test that sizing is reduced for lower confidence signals."""
    # 0.60 confidence -> 50% multiplier
    size = risk_engine.calculate_position_size(
        symbol="XAUUSD",
        entry_price=2350.0,
        stop_loss=2345.0,
        atr=2.0,
        current_equity=10000.0,
        confidence=0.60
    )
    assert size == 0.1 # 0.2 * 0.5

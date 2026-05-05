import pytest
import pandas as pd
from src.trading.risk_engine import RiskEngine
from src.core.config import TradingConfig

@pytest.fixture
def risk_engine():
    cfg = TradingConfig(MT5_PASSWORD="test", MT5_SERVER="test")
    return RiskEngine(cfg, 10000.0)

def test_drawdown_breaker(risk_engine):
    risk_engine.update_metrics(6000.0) # 40% drawdown
    assert not risk_engine._check_drawdown_breaker()

def test_daily_loss_breaker(risk_engine):
    risk_engine.update_metrics(10000.0, realized_pnl=-600.0) # 6% loss
    assert not risk_engine._check_daily_loss_breaker()

def test_calculate_position_size(risk_engine):
    data = pd.DataFrame({
        "atr": [1.0] * 100,
        "close": [2300.0] * 100
    })
    size = risk_engine.calculate_position_size("XAUUSD", data)
    assert size >= 0.01

def test_validate_signal_rejection(risk_engine):
    class MockSignal:
        def __init__(self):
            self.symbol = "XAUUSD"
            self.direction = 1
            self.confidence = 0.4 # Below default 0.55

    data = pd.DataFrame({"atr": [1.0], "close": [2300.0]})
    decision = risk_engine.validate_signal(MockSignal(), data, [])
    assert not decision.is_approved
    assert "Confidence" in decision.reason

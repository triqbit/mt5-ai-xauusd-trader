import pytest
import pandas as pd
from src.trading.risk_manager import RiskManager
from src.core.config import TradingConfig
from src.core.schemas import TradeSignal
from src.core.constants import SignalDirection

@pytest.fixture
def risk_manager():
    cfg = TradingConfig(MT5_PASSWORD="test", MT5_SERVER="test")
    return RiskManager(cfg, 10000.0)

def test_drawdown_breaker(risk_manager):
    risk_manager.update_equity(6000.0) # 40% drawdown (threshold is 30% in TradingConfig default)
    assert not risk_manager._check_circuit_breaker()

def test_daily_loss_breaker(risk_manager):
    risk_manager.update_equity(10000.0)
    risk_manager.record_pnl(-600.0) # 6% loss (threshold is 5% in TradingConfig default)
    assert risk_manager.get_daily_loss_level() >= 4

def test_calculate_position_size(risk_manager):
    data = pd.DataFrame({
        "atr": [1.0] * 100,
        "close": [2300.0] * 100
    })
    size = risk_manager.calculate_position_size("XAUUSD", data)
    assert size >= 0.01

def test_approve_signal_rejection(risk_manager):
    signal = TradeSignal(
        symbol="XAUUSD",
        direction=SignalDirection.BUY,
        entry_price=2300.0,
        stop_loss=2290.0,
        take_profit=2320.0,
        lot_size=0.1,
        algorithm="ppo",
        confidence=0.4 # Below default 0.55
    )

    data = pd.DataFrame({"atr": [1.0], "close": [2300.0]})
    decision = risk_manager.approve(signal, market_data=data, open_positions=[])
    assert not decision.is_approved
    assert "Confidence" in decision.reason

def test_approve_signal_success(risk_manager):
    signal = TradeSignal(
        symbol="XAUUSD",
        direction=SignalDirection.BUY,
        entry_price=2300.0,
        stop_loss=2290.0,
        take_profit=2320.0,
        lot_size=0.1,
        algorithm="ppo",
        confidence=0.8
    )

    data = pd.DataFrame({"atr": [1.0], "close": [2300.0]})
    # Mocking ALLOCATION_WEIGHTS isn't strictly necessary if using XAUUSD
    decision = risk_manager.approve(signal, market_data=data, open_positions=[])
    assert decision.is_approved
    assert decision.adjusted_lot_size > 0

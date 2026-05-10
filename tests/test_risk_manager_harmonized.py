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

def test_8_layer_cascade_confidence_failure(risk_manager):
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
    decision = risk_manager.approve(signal)
    assert not decision.is_approved
    assert "Confidence" in decision.reason
    assert not decision.trace["prediction_limits"]["passed"]

def test_atr_based_position_sizing(risk_manager):
    # Setup data where current ATR == average ATR (ratio 1.0)
    # 8640 is the tail size for avg_atr in RiskManager
    data = pd.DataFrame({
        "atr": [1.0] * 9000,
        "close": [2300.0] * 9000
    })
    # Mock balance to 100,000 for easier math
    risk_manager.balance = 100000.0
    risk_manager.cfg.risk_per_trade = 0.01
    size = risk_manager.calculate_position_size("XAUUSD", data)
    # Risk 1% of 100000 = 1000. ATR 1.0 * 100 = 100 per lot. So 10 lots.
    # HOWEVER, max_position_size_pct is 10% (0.10) of equity.
    # 10% of 100000 = 10000.
    # 10000 / (2300 * 100) = 0.043... lots.
    # The 10% max notional cap is hit!
    assert 0.03 <= size <= 0.05

def test_drawdown_circuit_breaker(risk_manager):
    # cfg.max_drawdown defaults to 0.30
    risk_manager.update_equity(6500.0) # > 30% drawdown
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
    decision = risk_manager.approve(signal)
    assert not decision.is_approved
    assert "drawdown" in decision.reason.lower()

def test_directional_exposure_limit(risk_manager):
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
    # 30% of 10000 = 3000.
    # 1.5 lots at 2300 = 1.5 * 2300 * 100 = 345,000 NOTIONAL.
    # Wait, my check_directional_exposure uses price_estimate = 2300.0
    # exposure_pct = (abs(net_lots) * 2300 * 100) / balance
    # To hit 30% (0.3): net_lots * 230000 / 10000 = 0.3 => net_lots = 0.013
    # Actually, min_lot_size is 0.01. 1 lot is already 230,000 / 10000 = 23.0 (2300% exposure)
    # The 30% limit in code is: exposure_pct <= 0.30
    # So if I have 1 lot, it should fail.

    open_positions = [{"symbol": "XAUUSD", "volume": 0.02, "type": 0}] # Already has 0.02 lots BUY
    decision = risk_manager.approve(signal, open_positions=open_positions)
    assert not decision.is_approved
    assert "directional exposure" in decision.reason.lower()

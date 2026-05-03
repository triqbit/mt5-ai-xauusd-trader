import pytest
from src.trading.risk_engine import RiskEngine, TradeSignal
from src.core.config import get_config

@pytest.fixture
def risk_engine():
    cfg = get_config()
    return RiskEngine(cfg, account_balance=10000.0)

def test_daily_loss_cascading(risk_engine):
    # L1: 2%
    risk_engine.daily.realised_pnl = -200.0 # 2% of 10000
    assert risk_engine.check_daily_loss_cascading() == 1.0

    # L2: 3%
    risk_engine.daily.realised_pnl = -300.0
    assert risk_engine.check_daily_loss_cascading() == 0.50

    # L3: 4%
    risk_engine.daily.realised_pnl = -400.0
    assert risk_engine.check_daily_loss_cascading() == 0.25

    # L4: 5%
    risk_engine.daily.realised_pnl = -500.0
    assert risk_engine.check_daily_loss_cascading() == 0.0

    # Hard Stop: 6%
    risk_engine.daily.realised_pnl = -600.0
    assert risk_engine.check_daily_loss_cascading() == 0.0

def test_drawdown_levels(risk_engine):
    # L2: 15%
    risk_engine.balance = 8500.0
    assert risk_engine.check_drawdown_levels() == 0.75

    # L3: 20%
    risk_engine.balance = 8000.0
    assert risk_engine.check_drawdown_levels() == 0.50

    # L4: 25%
    risk_engine.balance = 7500.0
    assert risk_engine.check_drawdown_levels() == 0.0

    # L5: 30%
    risk_engine.balance = 7000.0
    assert risk_engine.check_drawdown_levels() == 0.0

def test_atr_position_sizing(risk_engine):
    equity = 10000.0
    atr = 5.0
    symbol = "XAUUSD"

    # risk_per_trade = 0.01 (1%) -> $100 risk
    # stop_dist = 2 * ATR = 10.0
    # lots = 100 / (10 * 100) = 0.10
    lots = risk_engine.calculate_atr_position_size(equity, atr, symbol)
    assert lots == 0.10

def test_validate_signal_streaks(risk_engine):
    signal = TradeSignal(
        symbol="XAUUSD",
        direction=1,
        entry_price=2300.0,
        stop_loss=2290.0,
        take_profit=2320.0,
        lot_size=0.1,
        algorithm="ppo",
        confidence=0.8
    )

    risk_engine.daily.consecutive_losses = 3
    assert risk_engine.validate_signal(signal) is False

    risk_engine.daily.consecutive_losses = 0
    assert risk_engine.validate_signal(signal) is True

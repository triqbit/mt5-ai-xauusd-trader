from unittest.mock import MagicMock

import pytest

from src.trading.risk_manager import RiskManager, TradeSignal


@pytest.fixture
def config():
    cfg = MagicMock()
    cfg.risk_per_trade = 0.01
    cfg.max_daily_loss = 0.05
    cfg.max_positions = 3
    return cfg

@pytest.fixture
def risk_manager(config):
    return RiskManager(config=config, account_balance=10000.0)

def test_daily_loss_scaling(risk_manager):
    # Set peak equity
    risk_manager.daily.peak_equity = 10000.0

    # No loss
    assert risk_manager._get_daily_loss_scale() == 1.0

    # 2.5% loss (Level 1)
    risk_manager.daily.realised_pnl = -250.0
    assert risk_manager._get_daily_loss_scale() == 1.0

    # 3.5% loss (Level 2)
    risk_manager.daily.realised_pnl = -350.0
    assert risk_manager._get_daily_loss_scale() == 0.50

    # 4.5% loss (Level 3)
    risk_manager.daily.realised_pnl = -450.0
    assert risk_manager._get_daily_loss_scale() == 0.25

    # 5.5% loss (Level 4)
    risk_manager.daily.realised_pnl = -550.0
    assert risk_manager._get_daily_loss_scale() == 0.0

def test_volatility_scaling(risk_manager):
    risk_manager.update_atr_baseline(1.0)

    # Normal vol
    assert risk_manager._get_volatility_scale(1.2) == 1.0

    # High vol (1.6x)
    assert risk_manager._get_volatility_scale(1.6) == 0.75

    # Very high vol (2.1x)
    assert risk_manager._get_volatility_scale(2.1) == 0.50

    # Extreme vol (3.1x)
    assert risk_manager._get_volatility_scale(3.1) == 0.0

def test_approve_daily_loss_halt(risk_manager):
    risk_manager.daily.peak_equity = 10000.0
    risk_manager.daily.realised_pnl = -600.0 # 6% loss

    signal = TradeSignal(
        symbol="XAUUSD",
        direction=1,
        entry_price=2300.0,
        stop_loss=2290.0,
        take_profit=2320.0,
        lot_size=0.1,
        algorithm="test",
        confidence=0.8
    )

    assert risk_manager.approve(signal) is False

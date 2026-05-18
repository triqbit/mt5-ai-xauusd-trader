import pytest
from unittest.mock import MagicMock
from src.trading.risk_manager import RiskManager, DailyStats

@pytest.fixture
def mock_config():
    cfg = MagicMock()
    cfg.max_daily_loss = 0.05
    cfg.max_losing_streak = 3
    cfg.risk_per_trade = 0.01
    return cfg

def test_reconcile_state_empty(mock_config):
    risk = RiskManager(mock_config, account_balance=10000.0)
    risk.reconcile_state(10000.0, [])

    assert risk.balance == 10000.0
    assert risk.daily.realised_pnl == 0.0
    assert risk.daily.trade_count == 0
    assert risk.daily.consecutive_losses == 0

def test_reconcile_state_with_trades(mock_config):
    # Initial balance: 10000
    # Trades: +200, -100, -150, +300
    # Equity curve: 10000, 10200, 10100, 9950, 10250
    # Daily Peak: 10250
    # Final Balance: 10250
    # Streak: 0 (last was win)

    risk = RiskManager(mock_config, account_balance=10000.0)
    pnls = [200.0, -100.0, -150.0, 300.0]

    risk.reconcile_state(10000.0, pnls)

    assert risk.balance == 10250.0
    assert risk.daily.realised_pnl == 250.0
    assert risk.daily.trade_count == 4
    assert risk.daily.peak_equity == 10250.0
    assert risk.daily.consecutive_losses == 0

def test_reconcile_state_streak_and_drawdown(mock_config):
    # Initial balance: 10000
    # Trades: +100, -50, -50, -50
    # Equity curve: 10000, 10100, 10050, 10000, 9950
    # Daily Peak: 10100
    # Final Balance: 9950
    # Streak: 3

    risk = RiskManager(mock_config, account_balance=10000.0)
    pnls = [100.0, -50.0, -50.0, -50.0]

    risk.reconcile_state(10000.0, pnls)

    assert risk.balance == 9950.0
    assert risk.daily.realised_pnl == -50.0
    assert risk.daily.trade_count == 4
    assert risk.daily.peak_equity == 10100.0
    assert risk.daily.consecutive_losses == 3
    assert risk.peak_equity == 10100.0

def test_reconcile_state_complex_peak(mock_config):
    # Initial balance: 10000
    # Trades: +500, -200, +100, -100
    # Equity curve: 10000, 10500, 10300, 10400, 10300
    # Daily Peak: 10500

    risk = RiskManager(mock_config, account_balance=10000.0)
    pnls = [500.0, -200.0, 100.0, -100.0]

    risk.reconcile_state(10000.0, pnls)

    assert risk.daily.peak_equity == 10500.0
    assert risk.balance == 10300.0
    assert risk.daily.consecutive_losses == 1

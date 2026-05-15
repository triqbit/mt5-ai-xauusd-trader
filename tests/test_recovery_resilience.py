import pytest
from datetime import datetime, UTC, timedelta
from unittest.mock import MagicMock
from src.trading.risk_manager import RiskManager
from src.core.trade_logger import TradeLogger, Trade
from src.core.config import TradingConfig

class MockTrade:
    def __init__(self, pnl, updated_at=None):
        self.pnl = pnl
        self.updated_at = updated_at or datetime.now(UTC)

@pytest.fixture
def mk_config():
    cfg = MagicMock(spec=TradingConfig)
    cfg.risk_per_trade = 0.01
    cfg.max_losing_streak = 3
    cfg.max_daily_loss = 0.05
    cfg.max_drawdown = 0.15
    cfg.max_positions = 5
    cfg.symbol = "XAUUSD"
    cfg.min_confidence = 0.55
    return cfg

def test_risk_manager_reconcile_peak_equity(mk_config):
    # Setup: Starting balance 10000.
    # Trades: +500, +500, -2000. Peak was 11000. Current balance 9000.
    trade_logger = MagicMock(spec=TradeLogger)
    trade_logger.get_reconciliation_data.return_value = {
        "all_pnls": [500.0, 500.0, -2000.0],
        "today_trades": []
    }

    rm = RiskManager(mk_config, account_balance=9000.0, logger_db=trade_logger)
    rm.reconcile_state()

    # Starting balance was 9000 - (500 + 500 - 2000) = 9000 - (-1000) = 10000
    # Peak was 10000 -> 10500 -> 11000 -> 9000.
    assert rm.peak_equity == 11000.0
    assert rm.balance == 9000.0

    # Drawdown is (11000 - 9000) / 11000 = 18.18%
    # Should trigger circuit breaker (limit 15%)
    assert rm._check_circuit_breaker() is False

def test_risk_manager_reconcile_daily_stats(mk_config):
    trade_logger = MagicMock(spec=TradeLogger)

    today = datetime.now(UTC)
    t1 = MockTrade(pnl=-100.0, updated_at=today - timedelta(minutes=10))
    t2 = MockTrade(pnl=-200.0, updated_at=today - timedelta(minutes=5))

    trade_logger.get_reconciliation_data.return_value = {
        "all_pnls": [-100.0, -200.0],
        "today_trades": [t1, t2]
    }

    rm = RiskManager(mk_config, account_balance=9700.0, logger_db=trade_logger)
    rm.reconcile_state()

    assert rm.daily.realised_pnl == -300.0
    assert rm.daily.trade_count == 2
    assert rm.daily.consecutive_losses == 2
    # peak_equity should be 10000
    assert rm.peak_equity == 10000.0

def test_risk_manager_reconcile_no_data(mk_config):
    trade_logger = MagicMock(spec=TradeLogger)
    trade_logger.get_reconciliation_data.return_value = {
        "all_pnls": [],
        "today_trades": []
    }

    rm = RiskManager(mk_config, account_balance=10000.0, logger_db=trade_logger)
    rm.peak_equity = 12000.0 # Pretend it was higher
    rm.reconcile_state()

    assert rm.peak_equity == 12000.0
    assert rm.daily.realised_pnl == 0.0
    assert rm.daily.trade_count == 0

import pytest
import os
from unittest.mock import MagicMock, patch
from src.trading.risk_manager import RiskManager, TradeSignal, DailyStats
from src.core.config import TradingConfig, get_config

@pytest.fixture
def mock_cfg():
    with patch.dict(os.environ, {
        "MT5_PASSWORD": "test",
        "MT5_SERVER": "test",
        "MODE": "demo",
        "RISK_PER_TRADE": "0.01"
    }):
        get_config.cache_clear()
        return get_config()

def test_risk_manager_initialization(mock_cfg):
    risk = RiskManager(mock_cfg, account_balance=10000.0)
    assert risk.balance == 10000.0
    assert risk.peak_equity == 10000.0
    assert isinstance(risk.daily, DailyStats)

def test_risk_manager_update_equity(mock_cfg):
    risk = RiskManager(mock_cfg, account_balance=10000.0)
    risk.update_equity(11000.0)
    assert risk.balance == 11000.0
    assert risk.peak_equity == 11000.0
    assert risk.daily.peak_equity == 11000.0

    risk.update_equity(9000.0)
    assert risk.balance == 9000.0
    assert risk.peak_equity == 11000.0 # Peak should remain

def test_risk_manager_record_pnl(mock_cfg):
    risk = RiskManager(mock_cfg, account_balance=10000.0)
    risk.record_pnl(500.0)
    assert risk.daily.realised_pnl == 500.0
    assert risk.daily.trade_count == 1

def test_risk_manager_reset_daily(mock_cfg):
    monitor = MagicMock()
    risk = RiskManager(mock_cfg, account_balance=10000.0, monitor=monitor)
    risk.record_pnl(500.0)
    risk.reset_daily()
    monitor.send_daily_summary.assert_called_once_with(500.0, 1)
    assert risk.daily.realised_pnl == 0.0
    assert risk.daily.trade_count == 0

def test_risk_manager_size_position(mock_cfg):
    risk = RiskManager(mock_cfg, account_balance=10000.0)
    # Win rate 0.6, avg win 200, avg loss 100
    # Kelly = (0.6*200 - 0.4*100) / 200 = (120 - 40) / 200 = 80 / 200 = 0.4
    # Capped at 0.25
    # Risk capital = 10000 * 0.01 = 100
    # Lot size = (100 * 0.25) / (100 * 1.0) = 25 / 100 = 0.25
    lot = risk.size_position("XAUUSD", 0.6, 200.0, 100.0)
    assert lot == 0.25

def test_risk_manager_size_position_zero_loss(mock_cfg):
    risk = RiskManager(mock_cfg, account_balance=10000.0)
    lot = risk.size_position("XAUUSD", 0.6, 200.0, 0.0)
    assert lot == 0.01

def test_risk_manager_approve_rejections(mock_cfg):
    risk = RiskManager(mock_cfg, account_balance=10000.0)

    # 1. Symbol not in portfolio
    signal = TradeSignal("INVALID", 1, 2000, 1990, 2020, 0.1, "test", 0.8)
    assert risk.approve(signal) is False

    # 2. Low confidence
    signal = TradeSignal("XAUUSD", 1, 2000, 1990, 2020, 0.1, "test", 0.4)
    assert risk.approve(signal) is False

    # 3. Risk/Reward too low
    signal = TradeSignal("XAUUSD", 1, 2000, 1995, 2002, 0.1, "test", 0.8)
    assert risk.approve(signal) is False

def test_risk_manager_daily_loss_limit(mock_cfg):
    risk = RiskManager(mock_cfg, account_balance=10000.0)
    risk.record_pnl(-600.0) # 6% loss, exceeds 5% limit
    signal = TradeSignal("XAUUSD", 1, 2000, 1990, 2020, 0.1, "test", 0.8)
    assert risk.approve(signal) is False

def test_risk_manager_max_positions(mock_cfg):
    risk = RiskManager(mock_cfg, account_balance=10000.0)
    risk.open_positions = {"A": 1, "B": 2, "C": 3} # Max is 3
    signal = TradeSignal("XAUUSD", 1, 2000, 1990, 2020, 0.1, "test", 0.8)
    assert risk.approve(signal) is False

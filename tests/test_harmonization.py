"""Tests ensuring all core modules harmonize and respect enterprise standards."""
import pytest
from src.core.config import get_config

def test_risk_manager_consolidated_initialization():
    """Verify RiskEngine can be initialized with both logger and monitor."""
    from src.trading.risk_engine import RiskEngine
    from src.core.trade_logger import TradeLogger
    from src.core.monitor import Monitor

    cfg = get_config()
    trade_logger = TradeLogger(db_url="sqlite:///:memory:")
    mock_monitor = Monitor(cfg)

    risk = RiskEngine(
        cfg,
        account_balance=10000.0,
        logger_db=trade_logger,
        monitor=mock_monitor
    )
    assert risk.balance == 10000.0
    assert risk.trade_logger == trade_logger
    assert risk.monitor == mock_monitor

def test_config_singleton_loading():
    """Ensure get_config() returns the same instance (singleton)."""
    c1 = get_config()
    c2 = get_config()
    assert c1 is c2

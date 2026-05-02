"""
Tests for system harmonization and cross-agent conflict resolution.
"""

import pytest
from unittest.mock import MagicMock, patch


def test_risk_manager_consolidated_initialization():
    """Verify RiskManager can be initialized with both logger and monitor."""
    from src.trading.risk_manager import RiskManager
    from src.core.trade_logger import TradeLogger
    from src.core.monitor import Monitor
    from src.core.config import TradingConfig

    config = MagicMock(spec=TradingConfig)
    logger = MagicMock(spec=TradeLogger)
    monitor = MagicMock(spec=Monitor)

    risk = RiskManager(config=config, account_balance=10000.0, logger_db=logger, monitor=monitor)

    assert risk.trade_logger == logger
    assert risk.monitor == monitor
    assert risk.balance == 10000.0


def test_config_singleton_loading():
    """Verify get_config returns a TradingConfig singleton."""
    # Ensure environment variables required for validation are present and valid
    with patch.dict(
        "os.environ", {"MT5_PASSWORD": "dummy", "MT5_SERVER": "dummy", "RISK_PER_TRADE": "0.01"}
    ):
        from src.core.config import get_config, TradingConfig

        # We need to clear the lru_cache for testing purpose if it was already populated
        get_config.cache_clear()
        cfg1 = get_config()
        cfg2 = get_config()
        assert isinstance(cfg1, TradingConfig)
        assert cfg1 is cfg2

import pytest
import os
from unittest.mock import MagicMock
from src.core.config import TradingConfig
from src.core.trade_logger import TradeLogger
from src.trading.mt5_connector import MT5Connector

@pytest.fixture
def test_cfg(monkeypatch):
    monkeypatch.setenv("MT5_PASSWORD", "testpass")
    monkeypatch.setenv("MT5_SERVER", "TestServer")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///test_integration.db")
    cfg = TradingConfig()
    return cfg

@pytest.fixture
def db_logger():
    db_path = "test_integration.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    logger = TradeLogger(db_url=f"sqlite:///{db_path}")
    yield logger
    if os.path.exists(db_path):
        os.remove(db_path)

@pytest.fixture
def mock_connector():
    connector = MagicMock(spec=MT5Connector)
    connector.get_account_balance.return_value = 10000.0
    return connector

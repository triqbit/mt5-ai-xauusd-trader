import os
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.core.config import TradingConfig
from src.core.monitor import Monitor
from src.core.trade_logger import TradeLogger
from src.trading.mt5_connector import MT5Connector


@pytest.fixture
def test_config():
    return TradingConfig(
        mt5_login=123456,
        mt5_password="test_password",
        mt5_server="TestServer",
        metaapi_token="test_token",
        metaapi_account_id="test_account",
        database_url="sqlite:///test_integration.db",
        telegram_token="test_bot_token",
        telegram_chat_id="test_chat_id"
    )

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
def mock_mt5(monkeypatch):
    mock = MagicMock()
    # MT5 constants
    mock.TRADE_RETCODE_DONE = 10009
    mock.last_error.return_value = (0, "Success")

    # Mock some basic functions
    mock.initialize.return_value = True
    mock.shutdown.return_value = None

    monkeypatch.setattr("src.trading.mt5_connector.mt5", mock)
    monkeypatch.setattr("src.trading.mt5_connector.MT5_AVAILABLE", True)
    return mock

@pytest.fixture
def mock_metaapi(monkeypatch):
    mock_api = MagicMock()
    monkeypatch.setattr("src.trading.mt5_connector.MetaApi", mock_api)
    monkeypatch.setattr("src.trading.mt5_connector.METAAPI_AVAILABLE", True)
    return mock_api

@pytest.fixture
def mock_telegram(monkeypatch):
    mock_bot = MagicMock()
    # Mock send_message to be an AsyncMock as Monitor expects it to be async
    mock_bot.send_message = AsyncMock()

    # Patch the telegram.Bot class to return our mock_bot
    monkeypatch.setattr("telegram.Bot", MagicMock(return_value=mock_bot))
    return mock_bot

@pytest.fixture
def monitor(test_config, mock_telegram):
    return Monitor(test_config)

@pytest.fixture
def connector(test_config, mock_mt5):
    return MT5Connector(test_config)

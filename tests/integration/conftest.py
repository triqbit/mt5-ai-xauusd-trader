import pytest
import os
from unittest.mock import MagicMock, patch
from src.core.config import TradingConfig
from src.core.trade_logger import TradeLogger
from src.core.monitor import Monitor

@pytest.fixture
def mock_config():
    config = MagicMock(spec=TradingConfig)
    config.mt5_login = 12345
    config.mt5_password = "password"
    config.mt5_server = "server"
    config.mt5_path = "path/to/mt5"
    config.metaapi_token = "fake_token"
    config.metaapi_account_id = "fake_id"
    config.symbol = "XAUUSD"
    config.timeframe = "M5"
    config.mode = "demo"
    config.max_positions = 3
    config.risk_per_trade = 0.01
    config.max_daily_loss = 0.05
    config.algorithm = "ensemble"
    config.database_url = "sqlite:///test_integration.db"
    config.telegram_token = "fake_telegram_token"
    config.telegram_chat_id = "fake_chat_id"
    config.confidence_threshold = 0.6
    return config

@pytest.fixture
def db_logger(mock_config):
    db_path = "test_integration.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    logger = TradeLogger(db_url=mock_config.database_url)
    yield logger
    if os.path.exists(db_path):
        os.remove(db_path)

@pytest.fixture
def mock_mt5():
    with patch("src.trading.mt5_connector.mt5") as mock:
        mock.initialize.return_value = True
        mock.last_error.return_value = (0, "Success")
        mock.ORDER_TYPE_BUY = 0
        mock.ORDER_TYPE_SELL = 1
        mock.TRADE_ACTION_DEAL = 1
        mock.ORDER_TIME_GTC = 1
        mock.ORDER_FILLING_IOC = 1
        mock.TRADE_RETCODE_DONE = 10009

        # Mock result for order_send
        mock_result = MagicMock()
        mock_result.retcode = 10009
        mock_result.order = 123456
        mock_result.comment = "Done"
        mock.order_send.return_value = mock_result

        # Mock copy_rates_from_pos to return something by default
        import numpy as np
        mock.copy_rates_from_pos.return_value = np.array([
            (1713532800, 2380.0, 2385.0, 2375.0, 2382.0, 100, 0, 0),
        ], dtype=[('time', '<i8'), ('open', '<f8'), ('high', '<f8'), ('low', '<f8'), ('close', '<f8'), ('tick_volume', '<i8'), ('spread', '<i8'), ('real_volume', '<i8')])

        mock_tick = MagicMock()
        mock_tick.bid = 2381.0
        mock_tick.ask = 2382.0
        mock.symbol_info_tick.return_value = mock_tick

        yield mock

@pytest.fixture
def mock_metaapi():
    with patch("src.trading.mt5_connector.MetaApi") as mock:
        yield mock

@pytest.fixture
def mock_telegram():
    with patch("telegram.Bot") as mock:
        yield mock

@pytest.fixture
def monitor(mock_config, mock_telegram):
    return Monitor(mock_config)

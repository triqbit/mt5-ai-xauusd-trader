import pytest
from unittest.mock import MagicMock, patch
from src.trading.mt5_connector import MT5Connector
from src.core.config import get_config

@pytest.fixture
def mock_config():
    cfg = get_config()
    cfg.mt5_login = 123456
    cfg.mt5_password = "password"
    cfg.mt5_server = "server"
    cfg.metaapi_token = "token"
    cfg.metaapi_account_id = "account_id"
    return cfg

def test_mt5_initialization_success(mock_config):
    with patch("src.trading.mt5_connector.mt5") as mock_mt5:
        mock_mt5.initialize.return_value = True
        connector = MT5Connector(mock_config)
        assert connector.initialize() is True
        assert connector.use_metaapi is False

def test_mt5_failover_to_metaapi(mock_config):
    with patch("src.trading.mt5_connector.mt5") as mock_mt5, \
         patch("src.trading.mt5_connector.MetaApi") as mock_metaapi:

        # Native MT5 fails
        mock_mt5.initialize.return_value = False

        # Mock MetaAPI
        mock_api_instance = mock_metaapi.return_value
        mock_account_api = mock_api_instance.metatrader_account_api
        mock_account = MagicMock()
        mock_account_api.get_account.return_value = MagicMock() # Needs to be awaitable if _run_sync is used

        # Since _run_sync uses asyncio.run_until_complete, we need to mock the async calls properly
        # or mock the _run_sync itself for simplicity in this unit test

        connector = MT5Connector(mock_config)
        connector._run_sync = MagicMock()
        connector._run_sync.side_effect = [
            MagicMock(), # get_account
            MagicMock(), # connect
            MagicMock(), # wait_synchronized
        ]

        assert connector.initialize() is True
        assert connector.use_metaapi is True

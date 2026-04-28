"""Extended tests for src.trading.mt5_connector module."""
import pytest
from unittest.mock import MagicMock, patch
from src.core.config import TradingConfig
from src.trading.mt5_connector import MT5Connector

@pytest.fixture
def config():
    return TradingConfig(
        mt5_login=123, mt5_password="pw", mt5_server="srv",
        metaapi_token="token", metaapi_account_id="acc_id"
    )

def test_mt5_connector_initialization_failover(config):
    with patch("src.trading.mt5_connector.MT5_AVAILABLE", False), \
         patch("src.trading.mt5_connector.METAAPI_AVAILABLE", True), \
         patch("src.trading.mt5_connector.MetaApi") as mock_metaapi, \
         patch("src.trading.mt5_connector.MT5Connector._run_async") as mock_run_async:

        connector = MT5Connector(config)
        # Mocking background loop starting
        connector._loop = MagicMock()

        assert connector.initialize() is True
        assert connector.use_metaapi is True
        mock_metaapi.assert_called_once_with("token")
        assert mock_run_async.called

@pytest.mark.asyncio
async def test_mt5_connector_get_rates_metaapi_failover(config):
    with patch("src.trading.mt5_connector.MT5_AVAILABLE", False), \
         patch("src.trading.mt5_connector.METAAPI_AVAILABLE", True), \
         patch("src.trading.mt5_connector.MetaApi") as mock_metaapi, \
         patch("src.trading.mt5_connector.MT5Connector._run_async") as mock_run_async:

        connector = MT5Connector(config)

        # Setup mocks for persistent connection
        mock_connection = MagicMock()
        connector.metaapi_connection = mock_connection
        connector._is_initialized = True
        connector.use_metaapi = True
        connector._loop = MagicMock()

        import pandas as pd
        mock_run_async.return_value = pd.DataFrame([{"time": "2024-01-01", "close": 2000.0}])

        df = connector.get_rates("XAUUSD", "M5", 10)
        assert not df.empty
        assert df.iloc[0]["close"] == 2000.0
        assert mock_run_async.called

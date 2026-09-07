import pytest
from unittest.mock import MagicMock, patch
from src.trading.mt5_connector import MT5Connector

def test_mt5_to_metaapi_failover(mock_config, mock_mt5, mock_metaapi):
    # Setup: Native MT5 fails to initialize
    mock_mt5.initialize.return_value = False

    # MetaAPI is available and configured
    with patch("src.trading.mt5_connector.MT5_AVAILABLE", True), \
         patch("src.trading.mt5_connector.METAAPI_AVAILABLE", True):

        connector = MT5Connector(mock_config)
        success = connector.initialize()

        # Verify
        assert success is True
        assert connector.use_metaapi is True
        mock_mt5.initialize.assert_called_once()
        mock_metaapi.assert_called_once_with(mock_config.metaapi_token)

def test_graceful_degradation_all_failed(mock_config, mock_mt5, mock_metaapi):
    # Setup: Native MT5 fails
    mock_mt5.initialize.return_value = False

    # MetaAPI fails or not configured
    mock_config.metaapi_token = ""

    with patch("src.trading.mt5_connector.MT5_AVAILABLE", True), \
         patch("src.trading.mt5_connector.METAAPI_AVAILABLE", True):

        connector = MT5Connector(mock_config)
        success = connector.initialize()

        # Verify
        assert success is False
        assert connector._is_initialized is False
        mock_mt5.initialize.assert_called_once()
        mock_metaapi.assert_not_called()

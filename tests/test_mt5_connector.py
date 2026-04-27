import pytest
from unittest.mock import MagicMock, patch
from src.trading.mt5_connector import MT5Connector
from src.core.config import TradingConfig

@pytest.fixture
def mock_config():
    return TradingConfig(mt5_login=123, mt5_password="pw", mt5_server="srv")

def test_connector_initialization(mock_config):
    connector = MT5Connector(mock_config)
    assert not connector._is_initialized
    assert not connector.use_metaapi

@patch("src.trading.mt5_connector.mt5")
def test_native_mt5_success(mock_mt5, mock_config):
    """Test successful native MT5 initialization."""
    mock_mt5.initialize.return_value = True
    connector = MT5Connector(mock_config)

    with patch("src.trading.mt5_connector.MT5_AVAILABLE", True):
        assert connector.initialize()
        assert connector._is_initialized
        assert not connector.use_metaapi
        mock_mt5.initialize.assert_called_once()

@patch("src.trading.mt5_connector.mt5")
@patch("src.trading.mt5_connector.MetaApi")
def test_metaapi_fallback(mock_metaapi, mock_mt5, mock_config):
    """Test fallback to MetaAPI when native MT5 fails."""
    mock_mt5.initialize.return_value = False
    mock_config.metaapi_token = "token123"

    connector = MT5Connector(mock_config)

    with patch("src.trading.mt5_connector.MT5_AVAILABLE", True):
        with patch("src.trading.mt5_connector.METAAPI_AVAILABLE", True):
            assert connector.initialize()
            assert connector._is_initialized
            assert connector.use_metaapi
            mock_metaapi.assert_called_once_with("token123")

def test_get_rates_not_initialized(mock_config):
    connector = MT5Connector(mock_config)
    df = connector.get_rates("XAUUSD", "M5", 10)
    assert df.empty

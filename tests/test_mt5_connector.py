"""Tests for src.trading.mt5_connector module."""
import pytest
from unittest.mock import MagicMock, patch
from src.trading.mt5_connector import MT5Connector
from src.core.config import TradingConfig

@pytest.fixture
def config(monkeypatch):
    monkeypatch.setenv("MT5_LOGIN", "12345")
    monkeypatch.setenv("MT5_PASSWORD", "test")
    monkeypatch.setenv("MT5_SERVER", "test")
    return TradingConfig(
        metaapi_token="fake_token",
        metaapi_account_id="fake_id"
    )

def test_mt5_connector_initialization_fail_all(config):
    """Test behavior when both MT5 and MetaAPI fail."""
    with patch("src.trading.mt5_connector.MT5_AVAILABLE", False), \
         patch("src.trading.mt5_connector.METAAPI_AVAILABLE", False):
        connector = MT5Connector(config)
        assert connector.initialize() is False

def test_mt5_connector_metaapi_fallback(config):
    """Test fallback to MetaAPI when MT5 SDK is unavailable."""
    with patch("src.trading.mt5_connector.MT5_AVAILABLE", False), \
         patch("src.trading.mt5_connector.METAAPI_AVAILABLE", True), \
         patch("src.trading.mt5_connector.MetaApi") as mock_metaapi:
        connector = MT5Connector(config)
        assert connector.initialize() is True
        assert connector.use_metaapi is True
        mock_metaapi.assert_called_once_with("fake_token")

def test_mt5_connector_native_success(config):
    """Test successful native MT5 initialization."""
    with patch("src.trading.mt5_connector.MT5_AVAILABLE", True), \
         patch("src.trading.mt5_connector.mt5") as mock_mt5:
        mock_mt5.initialize.return_value = True
        connector = MT5Connector(config)
        assert connector.initialize() is True
        assert connector.use_metaapi is False
        mock_mt5.initialize.assert_called_once()

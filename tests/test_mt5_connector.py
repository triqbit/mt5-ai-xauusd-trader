"""Tests for MT5Connector module."""
import pytest
from unittest.mock import MagicMock, patch
from src.trading.mt5_connector import MT5Connector
from src.core.config import TradingConfig

@pytest.fixture
def config():
    return TradingConfig(
        mt5_password="test",
        mt5_server="test"
    )

def test_mt5_connector_initialization(config):
    with patch('src.trading.mt5_connector.MT5_AVAILABLE', False):
        conn = MT5Connector(config)
        assert conn._is_initialized is False

def test_mt5_connector_metaapi_fallback(config):
    config.metaapi_token = "token"
    config.metaapi_account_id = "id"
    with patch('src.trading.mt5_connector.MT5_AVAILABLE', False):
        with patch('src.trading.mt5_connector.METAAPI_AVAILABLE', True):
            with patch('src.trading.mt5_connector.MetaApi', MagicMock()):
                conn = MT5Connector(config)
                assert conn.initialize() is True
                assert conn.use_metaapi is True

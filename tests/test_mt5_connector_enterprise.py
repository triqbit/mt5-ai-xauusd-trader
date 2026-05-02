import pytest
import numpy as np
from unittest.mock import MagicMock, patch
from src.trading.mt5_connector import MT5Connector
from src.core.config import TradingConfig


@pytest.fixture
def mock_config():
    return TradingConfig(
        mt5_login=123,
        mt5_password="pwd",
        mt5_server="srv",
        metaapi_token="token",
        metaapi_account_id="acc_id",
    )


def test_connector_initialization_flow(mock_config):
    with patch("src.trading.mt5_connector.mt5") as mock_mt5:
        mock_mt5.initialize.return_value = True
        connector = MT5Connector(mock_config)
        assert connector.initialize() is True
        assert connector.use_metaapi is False


def test_connector_metaapi_fallback(mock_config):
    with (
        patch("src.trading.mt5_connector.mt5") as mock_mt5,
        patch("src.trading.mt5_connector.MetaApi") as mock_meta,
    ):
        # Fail native MT5
        mock_mt5.initialize.return_value = False
        # Setup MetaAPI mock
        mock_meta_instance = MagicMock()
        mock_meta.return_value = mock_meta_instance

        connector = MT5Connector(mock_config)
        assert connector.initialize() is True
        assert connector.use_metaapi is True


def test_get_rates_native(mock_config):
    with patch("src.trading.mt5_connector.mt5") as mock_mt5:
        mock_mt5.initialize.return_value = True
        mock_mt5.copy_rates_from_pos.return_value = np.array(
            [(1600000000, 1.0, 1.1, 0.9, 1.05, 100, 0, 0)],
            dtype=[
                ("time", "i8"),
                ("open", "f8"),
                ("high", "f8"),
                ("low", "f8"),
                ("close", "f8"),
                ("tick_volume", "i8"),
                ("spread", "i4"),
                ("real_volume", "i8"),
            ],
        )
        connector = MT5Connector(mock_config)
        connector.initialize()
        df = connector.get_rates("XAUUSD", "M5", 1)
        assert not df.empty
        assert "close" in df.columns

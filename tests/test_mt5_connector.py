import unittest
from unittest.mock import MagicMock, patch
import pandas as pd
from src.trading.mt5_connector import MT5Connector
from src.core.config import TradingConfig

class TestMT5Connector(unittest.TestCase):
    def setUp(self):
        self.config = MagicMock(spec=TradingConfig)
        self.config.mode = "demo"
        self.config.mt5_path = "C:/Program Files/MetaTrader 5/terminal64.exe"
        self.config.mt5_login = 12345
        self.config.mt5_password = "password"
        self.config.mt5_server = "Server"
        self.config.metaapi_token = "token"
        self.config.metaapi_account_id = "account_id"
        self.connector = MT5Connector(self.config)

    @patch("src.trading.mt5_connector.mt5")
    def test_initialize_native_success(self, mock_mt5):
        mock_mt5.initialize.return_value = True
        with patch("src.trading.mt5_connector.MT5_AVAILABLE", True):
            self.assertTrue(self.connector.initialize())
            self.assertFalse(self.connector.use_metaapi)

    @patch("src.trading.mt5_connector.mt5")
    @patch("src.trading.mt5_connector.MetaApi")
    def test_initialize_failover_to_metaapi(self, mock_metaapi, mock_mt5):
        mock_mt5.initialize.return_value = False
        with patch("src.trading.mt5_connector.MT5_AVAILABLE", True), \
             patch("src.trading.mt5_connector.METAAPI_AVAILABLE", True):
            self.assertTrue(self.connector.initialize())
            self.assertTrue(self.connector.use_metaapi)

    @patch("src.trading.mt5_connector.mt5")
    def test_get_rates_native(self, mock_mt5):
        self.connector._is_initialized = True
        self.connector.use_metaapi = False
        mock_mt5.copy_rates_from_pos.return_value = [{"time": 1234567890, "open": 1.0}]
        with patch("src.trading.mt5_connector.MT5_AVAILABLE", True):
            df = self.connector.get_rates("XAUUSD", "M5", 10)
            self.assertFalse(df.empty)
            self.assertIn("time", df.columns)

if __name__ == "__main__":
    unittest.main()

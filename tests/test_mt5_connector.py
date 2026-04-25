import unittest
from unittest.mock import MagicMock, patch
from src.trading.mt5_connector import MT5Connector
from src.core.config import TradingConfig

class TestMT5Connector(unittest.TestCase):
    def setUp(self):
        self.config = MagicMock(spec=TradingConfig)
        self.config.mode = "demo"
        self.config.mt5_path = "C:/Program Files/MetaTrader 5/terminal64.exe"
        self.config.mt5_login = 12345
        self.config.mt5_password = "password"
        self.config.mt5_server = "Broker-Server"
        self.config.metaapi_token = "token"
        self.config.metaapi_account_id = "account_id"
        self.connector = MT5Connector(self.config)

    @patch("src.trading.mt5_connector.mt5")
    def test_initialize_native_success(self, mock_mt5):
        mock_mt5.initialize.return_value = True
        with patch("src.trading.mt5_connector.MT5_AVAILABLE", True):
            result = self.connector.initialize()
            self.assertTrue(result)
            self.assertFalse(self.connector.use_metaapi)

    @patch("src.trading.mt5_connector.mt5")
    @patch("src.trading.mt5_connector.MetaApi")
    @patch("src.trading.mt5_connector.MT5Connector._run_coro")
    def test_initialize_metaapi_fallback(self, mock_run_coro, mock_metaapi, mock_mt5):
        mock_mt5.initialize.return_value = False
        mock_run_coro.return_value = MagicMock()
        with patch("src.trading.mt5_connector.MT5_AVAILABLE", True), \
             patch("src.trading.mt5_connector.METAAPI_AVAILABLE", True):
            result = self.connector.initialize()
            self.assertTrue(result)
            self.assertTrue(self.connector.use_metaapi)

if __name__ == "__main__":
    unittest.main()

import unittest
from unittest.mock import MagicMock, patch
from src.trading.mt5_connector import MT5Connector
from src.core.config import TradingConfig

class TestMT5Connector(unittest.TestCase):
    def setUp(self):
        self.config = MagicMock(spec=TradingConfig)
        self.config.mt5_path = "path/to/mt5"
        self.config.mt5_login = 12345
        self.config.mt5_password = "password"
        self.config.mt5_server = "server"
        self.config.mode = "demo"
        self.config.metaapi_token = "token"
        self.connector = MT5Connector(self.config)

    @patch("src.trading.mt5_connector.mt5")
    def test_initialize_native_success(self, mock_mt5):
        mock_mt5.initialize.return_value = True
        with patch("src.trading.mt5_connector.MT5_AVAILABLE", True):
            result = self.connector.initialize()
            self.assertTrue(result)
            self.assertFalse(self.connector.use_metaapi)
            mock_mt5.initialize.assert_called_once()

    @patch("src.trading.mt5_connector.mt5")
    @patch("src.trading.mt5_connector.MetaApi")
    def test_initialize_fallback_metaapi(self, mock_metaapi, mock_mt5):
        mock_mt5.initialize.return_value = False
        with patch("src.trading.mt5_connector.MT5_AVAILABLE", True):
            with patch("src.trading.mt5_connector.METAAPI_AVAILABLE", True):
                result = self.connector.initialize()
                self.assertTrue(result)
                self.assertTrue(self.connector.use_metaapi)
                self.assertIsNotNone(self.connector.metaapi)

    @patch("src.trading.mt5_connector.mt5")
    def test_health_check_native(self, mock_mt5):
        self.connector._is_initialized = True
        self.connector.use_metaapi = False
        mock_mt5.terminal_info.return_value.connected = True
        self.assertTrue(self.connector.health_check())

        mock_mt5.terminal_info.return_value.connected = False
        self.assertFalse(self.connector.health_check())

    @patch("src.trading.mt5_connector.mt5")
    def test_get_account_balance(self, mock_mt5):
        self.connector._is_initialized = True
        self.connector.use_metaapi = False
        mock_mt5.account_info.return_value._asdict.return_value = {"balance": 1000.0}
        self.assertEqual(self.connector.get_account_balance(), 1000.0)

if __name__ == "__main__":
    unittest.main()

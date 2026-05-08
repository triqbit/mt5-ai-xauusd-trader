
import unittest
from unittest.mock import MagicMock, patch
from src.core.health import HealthChecker, HealthStatus
from src.trading.mt5_connector import MT5Connector
from src.core.config import TradingConfig

class TestHealthExtended(unittest.TestCase):
    def setUp(self):
        self.config = MagicMock(spec=TradingConfig)
        self.config.symbol = "XAUUSD"
        self.connector = MagicMock(spec=MT5Connector)
        self.checker = HealthChecker(self.config, connector=self.connector)

    def test_check_environment(self):
        with patch("platform.python_version", return_value="3.10.0"), \
             patch("platform.system", return_value="Linux"), \
             patch("platform.release", return_value="5.4.0"):
            status = self.checker.check_environment()
            self.assertEqual(status.status, HealthStatus.HEALTHY)
            self.assertIn("Python 3.10.0", status.message)
            self.assertIn("Linux 5.4.0", status.message)

    def test_check_mt5_algo_trading_disabled(self):
        self.connector._is_initialized = True
        self.connector.get_account_info.return_value = {"trade_allowed": True}
        self.connector.get_terminal_status.return_value = {"algo_trading": False}
        self.connector.get_symbol_properties.return_value = {"tradable": True}

        status = self.checker.check_mt5()
        self.assertEqual(status.status, HealthStatus.DEGRADED)
        self.assertIn("Algo Trading is DISABLED", status.message)
        self.assertIn("Enable 'Algo Trading' button", status.remedy)

    def test_check_mt5_symbol_not_found_with_suggestions(self):
        self.connector._is_initialized = True
        self.connector.get_account_info.return_value = {"trade_allowed": True}
        self.connector.get_terminal_status.return_value = {"algo_trading": True}
        self.connector.get_symbol_properties.return_value = None
        self.connector.find_symbols.return_value = ["GOLD", "XAUUSD.m"]

        status = self.checker.check_mt5()
        self.assertEqual(status.status, HealthStatus.FAILED)
        self.assertIn("Symbol 'XAUUSD' not found", status.message)
        self.assertIn("GOLD, XAUUSD.m", status.message)
        self.assertIn("Check SYMBOL in .env", status.remedy)

if __name__ == "__main__":
    unittest.main()

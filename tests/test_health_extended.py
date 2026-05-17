
import unittest
from unittest.mock import MagicMock, patch

from src.core.config import TradingConfig
from src.core.health import HealthChecker, HealthStatus
from src.trading.mt5_connector import MT5Connector


class TestHealthExtended(unittest.TestCase):
    def setUp(self):
        self.config = MagicMock(spec=TradingConfig)
        self.config.symbol = "XAUUSD"
        self.config.is_live = False  # Default to demo for tests
        self.connector = MagicMock(spec=MT5Connector)
        self.checker = HealthChecker(self.config, connector=self.connector)

    def test_check_environment(self):
        with patch("platform.python_version", return_value="3.10.0"), \
             patch("platform.system", return_value="Linux"), \
             patch("platform.release", return_value="5.4.0"), \
             patch("platform.machine", return_value="x86_64"):
            status = self.checker.check_environment()
            self.assertEqual(status.status, HealthStatus.HEALTHY)
            self.assertIn("Python 3.10.0", status.message)
            self.assertIn("Linux 5.4.0", status.message)
            self.assertIn("x86_64", status.message)

    def test_check_system_resources_healthy(self):
        with patch("psutil.cpu_percent", return_value=10.0), \
             patch("psutil.virtual_memory") as mock_mem:
            mock_mem.return_value.percent = 20.0
            status = self.checker.check_system_resources()
            self.assertEqual(status.status, HealthStatus.HEALTHY)
            self.assertIn("CPU: 10.0%", status.message)
            self.assertIn("MEM: 20.0%", status.message)

    def test_check_system_resources_degraded_cpu(self):
        with patch("psutil.cpu_percent", return_value=95.0), \
             patch("psutil.virtual_memory") as mock_mem:
            mock_mem.return_value.percent = 20.0
            status = self.checker.check_system_resources()
            self.assertEqual(status.status, HealthStatus.DEGRADED)
            self.assertIn("CPU: 95.0%", status.message)
            self.assertIn("runaway processes", status.remedy)

    def test_check_system_resources_degraded_mem(self):
        with patch("psutil.cpu_percent", return_value=10.0), \
             patch("psutil.virtual_memory") as mock_mem:
            mock_mem.return_value.percent = 95.0
            status = self.checker.check_system_resources()
            self.assertEqual(status.status, HealthStatus.DEGRADED)
            self.assertIn("MEM: 95.0%", status.message)
            self.assertIn("memory leaks", status.remedy)

    def test_check_mt5_algo_trading_disabled(self):
        self.connector._is_initialized = True
        self.connector.get_account_info.return_value = {"trade_allowed": True}
        self.connector.get_terminal_status.return_value = {"algo_trading": False}
        self.connector.get_symbol_properties.return_value = {"tradable": True}

        # Case 1: Demo mode -> DEGRADED
        self.config.is_live = False
        status = self.checker.check_mt5()
        self.assertEqual(status.status, HealthStatus.DEGRADED)
        self.assertIn("Algo Trading is DISABLED", status.message)

        # Case 2: Live mode -> FAILED
        self.config.is_live = True
        status = self.checker.check_mt5()
        self.assertEqual(status.status, HealthStatus.FAILED)
        self.assertIn("Algo Trading is DISABLED", status.message)

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

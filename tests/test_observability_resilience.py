"""
Integration tests for enhanced observability of resilience and infrastructure state.
"""
import unittest
from unittest.mock import MagicMock, patch
from src.core.resilience import CircuitBreaker, CircuitState
from src.trading.mt5_connector import MT5Connector
from src.core.config import TradingConfig

class TestObservabilityResilience(unittest.TestCase):
    def setUp(self):
        self.mock_monitor = MagicMock()
        self.config = MagicMock()
        self.config.mode = "demo"
        self.config.symbol = "XAUUSD"
        self.config.mt5_server = "MockServer"
        self.config.mt5_login = 12345
        self.config.mt5_password.get_secret_value.return_value = "password"
        self.config.mt5_path = ""

    def test_circuit_breaker_updates_monitor(self):
        """Verify that CircuitBreaker calls monitor on state changes."""
        breaker = CircuitBreaker(
            name="TestBreaker",
            failure_threshold=2,
            recovery_timeout=0.1,
            monitor=self.mock_monitor
        )

        # Initial state should be recorded
        self.mock_monitor.update_circuit_breaker.assert_any_call("TestBreaker", "CLOSED")
        self.mock_monitor.update_circuit_breaker.reset_mock()

        # Trip the breaker
        def fail():
            raise ValueError("fail")

        wrapped_fail = breaker(fail)

        try:
            wrapped_fail()
        except ValueError:
            pass

        # Still CLOSED after 1 failure (threshold is 2)
        self.mock_monitor.update_circuit_breaker.assert_not_called()

        try:
            wrapped_fail()
        except ValueError:
            pass

        # Now it should be OPEN
        self.mock_monitor.update_circuit_breaker.assert_called_with("TestBreaker", "OPEN")

    def test_mt5_connector_updates_terminal_status(self):
        """Verify that MT5Connector updates terminal status metrics."""
        with patch("src.trading.mt5_connector.MT5_AVAILABLE", False):
            connector = MT5Connector(self.config, monitor=self.mock_monitor)

            # Mock get_terminal_status to return algo enabled
            connector.get_terminal_status = MagicMock(return_value={"algo_trading": True})

            # Manually trigger metric update
            connector._update_terminal_metrics()

            self.mock_monitor.update_terminal_status.assert_called_with(connected=False, algo_enabled=True)

if __name__ == "__main__":
    unittest.main()

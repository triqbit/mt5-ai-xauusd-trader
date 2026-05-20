"""
Verification tests for structured observability improvements.
"""

import unittest
from unittest.mock import MagicMock, patch

from src.core.monitor import Monitor
from src.core.resilience import CircuitBreaker
from src.trading.mt5_connector import MT5Connector


class TestStructuredObservability(unittest.TestCase):
    def test_circuit_breaker_logging(self):
        """Verify CircuitBreaker uses structured logging."""
        breaker = CircuitBreaker(name="TestBreaker", failure_threshold=1)

        with patch("src.core.resilience.logger") as mock_log:
            # Trigger failure to trip breaker
            def fail():
                raise ValueError("Test Error")

            wrapped = breaker(fail)
            with self.assertRaises(ValueError):
                wrapped()

            # Verify structured log call
            mock_log.error.assert_any_call(
                "circuit_breaker_tripped",
                name="TestBreaker",
                state="OPEN",
                from_state="CLOSED",
                failure_count=1,
                error="Test Error"
            )

    def test_mt5_connector_logging(self):
        """Verify MT5Connector uses structured logging."""
        mock_cfg = MagicMock()
        mock_cfg.mode = "demo"
        mock_cfg.symbol = "XAUUSD"
        mock_cfg.mt5_server = "MockServer"

        connector = MT5Connector(mock_cfg)

        from src.core.exceptions import MT5ConnectionError

        with patch("src.trading.mt5_connector.logger") as mock_log, \
             patch("src.trading.mt5_connector.MT5_AVAILABLE", False), \
             patch("src.trading.mt5_connector.METAAPI_AVAILABLE", False):
            with self.assertRaises(MT5ConnectionError):
                connector.initialize()

            # Verify structured log call for start
            mock_log.info.assert_any_call(
                "mt5_connector_initialization_started",
                mode="demo",
                symbol="XAUUSD",
                mt5_server="MockServer"
            )

    def test_main_loop_instrumentation(self):
        """
        Verify that Monitor methods for execution quality
        and model performance exist and are callable.
        """
        mock_cfg = MagicMock()
        mock_cfg.model_accuracy_floor = 0.5
        mock_cfg.model_drift_threshold = 0.3
        mock_cfg.model_calibration_threshold = 0.2
        mock_cfg.execution_latency_threshold = 0.5
        monitor = Monitor(mock_cfg)

        # These methods exist in src/core/monitor.py
        self.assertTrue(hasattr(monitor, "log_execution_quality"))
        self.assertTrue(hasattr(monitor, "log_model_performance"))

        # Test calling them (should not raise)
        monitor.log_execution_quality(latency_ms=100.0, slippage_pips=0.1, fill_rate=1.0)
        monitor.log_model_performance(accuracy=0.85, drift_score=0.05)

if __name__ == "__main__":
    unittest.main()

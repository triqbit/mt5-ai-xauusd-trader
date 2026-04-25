"""
Tests for Monitor class.
"""
import unittest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timezone, timedelta
from src.core.monitor import Monitor
from src.core.config import TradingConfig
from prometheus_client import REGISTRY

class TestMonitor(unittest.TestCase):
    def setUp(self):
        # Unregister existing collectors to avoid Duplicated timeseries error
        for c in list(REGISTRY._collector_to_names.keys()):
            REGISTRY.unregister(c)

        self.config = MagicMock(spec=TradingConfig)
        self.config.telegram_token = "fake_token"
        self.config.telegram_chat_id = "fake_chat_id"
        self.config.confidence_threshold = 0.6
        self.config.prometheus_port = 8000

        with patch('telegram.Bot'), patch('prometheus_client.start_http_server'):
            self.monitor = Monitor(self.config)

    def test_log_equity(self):
        self.monitor.log_equity(10000.0)
        self.assertEqual(len(self.monitor.equity_history), 1)
        self.assertEqual(self.monitor.equity_history[0]["equity"], 10000.0)
        self.assertIsInstance(self.monitor.equity_history[0]["timestamp"], datetime)

        # Check Prometheus metric
        from src.core.monitor import trading_equity
        self.assertEqual(trading_equity._value.get(), 10000.0)

    def test_log_trade(self):
        from src.core.monitor import trading_trades_total
        self.monitor.log_trade("buy")
        self.assertEqual(trading_trades_total.labels(side="buy")._value.get(), 1)

    def test_log_error(self):
        from src.core.monitor import trading_errors_total
        self.monitor.log_error("test_error")
        self.assertEqual(trading_errors_total.labels(error_type="test_error")._value.get(), 1)

    @patch('asyncio.run')
    def test_send_message(self, mock_asyncio_run):
        self.monitor.bot = MagicMock()
        self.monitor.bot.send_message = MagicMock()

        self.monitor.send_message("test message")

        mock_asyncio_run.assert_called_once()

    @patch('src.core.monitor.Monitor.send_message')
    def test_alert_circuit_breaker(self, mock_send_message):
        self.monitor.alert_circuit_breaker(0.15)
        mock_send_message.assert_called_once()
        self.assertIn("Circuit Breaker", mock_send_message.call_args[0][0])
        self.assertIn("15.00%", mock_send_message.call_args[0][0])

    @patch('src.core.monitor.Monitor.send_message')
    def test_send_daily_summary(self, mock_send_message):
        self.monitor.send_daily_summary(500.0, 10)
        mock_send_message.assert_called_once()
        self.assertIn("Daily Summary", mock_send_message.call_args[0][0])
        self.assertIn("500.00", mock_send_message.call_args[0][0])
        self.assertIn("10", mock_send_message.call_args[0][0])

        from src.core.monitor import trading_pnl_daily
        self.assertEqual(trading_pnl_daily._value.get(), 500.0)

    @patch('src.core.monitor.Monitor.send_message')
    def test_check_confidence_degradation(self, mock_send_message):
        from src.core.monitor import trading_model_confidence

        # Case 1: Below threshold
        self.monitor.check_confidence_degradation(0.5)
        mock_send_message.assert_called_once()
        self.assertIn("Confidence Degradation", mock_send_message.call_args[0][0])
        self.assertEqual(trading_model_confidence._value.get(), 0.5)

        mock_send_message.reset_mock()

        # Case 2: Throttling (within 1 hour)
        self.monitor.check_confidence_degradation(0.4)
        mock_send_message.assert_not_called()
        self.assertEqual(trading_model_confidence._value.get(), 0.4)

        # Case 3: After 1 hour
        self.monitor._last_confidence_alert = datetime.now(timezone.utc) - timedelta(hours=1, minutes=1)
        self.monitor.check_confidence_degradation(0.45)
        mock_send_message.assert_called_once()
        self.assertIn("0.450", mock_send_message.call_args[0][0])

        mock_send_message.reset_mock()

        # Case 4: Above threshold
        self.monitor.check_confidence_degradation(0.7)
        mock_send_message.assert_not_called()
        self.assertEqual(trading_model_confidence._value.get(), 0.7)

if __name__ == '__main__':
    unittest.main()

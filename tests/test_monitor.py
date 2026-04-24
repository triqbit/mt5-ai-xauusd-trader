"""
Tests for Monitor class.
"""
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta
from src.core.monitor import Monitor
from prometheus_client import REGISTRY

class TestMonitor(unittest.TestCase):
    def setUp(self):
        # Unregister all collectors to avoid "Duplicated timeseries" error
        for collector in list(REGISTRY._collector_to_names.keys()):
            REGISTRY.unregister(collector)

        self.config = MagicMock()
        self.config.telegram_token = "fake_token"
        self.config.telegram_chat_id = "fake_chat_id"
        self.config.confidence_threshold = 0.6
        self.config.prometheus_port = 8000

        with patch('telegram.Bot'), patch('prometheus_client.start_http_server'):
            # Re-importing inside setUp to ensure global metrics are registered
            # in the fresh REGISTRY
            import src.core.monitor
            import importlib
            importlib.reload(src.core.monitor)
            self.monitor = src.core.monitor.Monitor(self.config)

    def test_log_equity(self):
        self.monitor.log_equity(10000.0)
        self.assertEqual(len(self.monitor.equity_history), 1)
        self.assertEqual(self.monitor.equity_history[0]["equity"], 10000.0)
        self.assertEqual(REGISTRY.get_sample_value('trading_equity'), 10000.0)

    def test_log_trade(self):
        self.monitor.log_trade("buy", 0.1)
        self.assertEqual(REGISTRY.get_sample_value('trading_trades_total', {'side': 'buy'}), 1.0)

    def test_log_error(self):
        self.monitor.log_error("connection_error")
        self.assertEqual(REGISTRY.get_sample_value('trading_errors_total', {'error_type': 'connection_error'}), 1.0)

    @patch('asyncio.run')
    def test_send_message(self, mock_asyncio_run):
        self.monitor.bot = MagicMock()
        self.monitor.send_message("test message")
        mock_asyncio_run.assert_called_once()

    @patch('src.core.monitor.Monitor.send_message')
    def test_alert_circuit_breaker(self, mock_send_message):
        self.monitor.alert_circuit_breaker(0.15)
        mock_send_message.assert_called_once()
        self.assertIn("Circuit Breaker", mock_send_message.call_args[0][0])

    @patch('src.core.monitor.Monitor.send_message')
    def test_send_daily_summary(self, mock_send_message):
        self.monitor.send_daily_summary(500.0, 10)
        mock_send_message.assert_called_once()
        self.assertEqual(REGISTRY.get_sample_value('trading_pnl_daily'), 500.0)

    @patch('src.core.monitor.Monitor.send_message')
    def test_check_confidence_degradation(self, mock_send_message):
        # Case 1: Below threshold, alert sent
        self.monitor.check_confidence_degradation(0.5)
        mock_send_message.assert_called_once()
        self.assertEqual(REGISTRY.get_sample_value('trading_model_confidence'), 0.5)

        mock_send_message.reset_mock()

        # Case 2: Below threshold again, but throttled
        self.monitor.check_confidence_degradation(0.4)
        mock_send_message.assert_not_called()

        # Case 3: Below threshold, but after cooldown
        with patch('src.core.monitor.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime.now(timezone.utc) + timedelta(hours=2)
            self.monitor.check_confidence_degradation(0.45)
            mock_send_message.assert_called_once()

if __name__ == '__main__':
    unittest.main()

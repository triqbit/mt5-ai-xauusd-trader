"""
Tests for Monitor class.
"""
import unittest
import time
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
from src.core.monitor import Monitor
from src.core.config import TradingConfig
from prometheus_client import REGISTRY

class TestMonitor(unittest.TestCase):
    def setUp(self):
        # Unregister all collectors to avoid "Duplicated timeseries" error
        for collector in list(REGISTRY._collector_to_names.keys()):
            REGISTRY.unregister(collector)

        self.config = MagicMock(spec=TradingConfig)
        self.config.telegram_token = "fake_token"
        self.config.telegram_chat_id = "fake_chat_id"
        self.config.confidence_threshold = 0.6
        self.config.prometheus_port = 8000

        with patch('telegram.Bot'), patch('prometheus_client.start_http_server'):
            self.monitor = Monitor(self.config)

    def test_log_equity(self):
        with patch.object(self.monitor.metric_equity, 'set') as mock_set:
            self.monitor.log_equity(10000.0)
            self.assertEqual(len(self.monitor.equity_history), 1)
            self.assertEqual(self.monitor.equity_history[0]["equity"], 10000.0)
            self.assertIsInstance(self.monitor.equity_history[0]["timestamp"], datetime)
            mock_set.assert_called_once_with(10000.0)

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
        self.assertEqual(mock_send_message.call_args[1]["alert_type"], "circuit_breaker")

    @patch('src.core.monitor.Monitor.send_message')
    def test_send_daily_summary(self, mock_send_message):
        with patch.object(self.monitor.metric_daily_pnl, 'set') as mock_set:
            self.monitor.send_daily_summary(500.0, 10)
            mock_send_message.assert_called_once()
            self.assertIn("Daily Summary", mock_send_message.call_args[0][0])
            self.assertIn("500.00", mock_send_message.call_args[0][0])
            self.assertIn("10", mock_send_message.call_args[0][0])
            mock_set.assert_called_once_with(500.0)

    @patch('src.core.monitor.Monitor.send_message')
    def test_check_confidence_degradation(self, mock_send_message):
        with patch.object(self.monitor.metric_confidence, 'set') as mock_set:
            # Case 1: Below threshold
            self.monitor.check_confidence_degradation(0.5)
            mock_send_message.assert_called_once()
            self.assertIn("Confidence Degradation", mock_send_message.call_args[0][0])
            self.assertEqual(mock_send_message.call_args[1]["alert_type"], "confidence_degradation")
            mock_set.assert_called_once_with(0.5)

            mock_send_message.reset_mock()
            mock_set.reset_mock()

            # Case 2: Above threshold
            self.monitor.check_confidence_degradation(0.7)
            mock_send_message.assert_not_called()
            mock_set.assert_called_once_with(0.7)

    def test_equity_history_maxlen(self):
        # Fill equity history beyond maxlen
        for i in range(1100):
            self.monitor.log_equity(float(i))

        self.assertEqual(len(self.monitor.equity_history), 1000)
        self.assertEqual(self.monitor.equity_history[-1]["equity"], 1099.0)

    @patch('asyncio.run')
    def test_alert_throttling(self, mock_asyncio_run):
        self.monitor.bot = MagicMock()
        self.monitor._alert_cooldown = 10 # 10 seconds

        # Send first alert
        self.monitor.send_message("alert 1", alert_type="test_alert")
        self.assertEqual(mock_asyncio_run.call_count, 1)

        # Send second alert immediately (should be throttled)
        self.monitor.send_message("alert 2", alert_type="test_alert")
        self.assertEqual(mock_asyncio_run.call_count, 1)

        # Different alert type should not be throttled
        self.monitor.send_message("alert 3", alert_type="other_alert")
        self.assertEqual(mock_asyncio_run.call_count, 2)

        # Fast-forward time for first alert type
        with patch('time.time', return_value=time.time() + 20):
             self.monitor.send_message("alert 4", alert_type="test_alert")
             self.assertEqual(mock_asyncio_run.call_count, 3)

if __name__ == '__main__':
    unittest.main()

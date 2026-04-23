"""
Tests for Monitor class.
"""
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime
from prometheus_client import REGISTRY
from src.core.monitor import Monitor
from src.core.config import TradingConfig

class TestMonitor(unittest.TestCase):
    def setUp(self):
        # Unregister all collectors to avoid "Duplicated timeseries" error
        collectors = list(REGISTRY._collector_to_names.keys())
        for collector in collectors:
            REGISTRY.unregister(collector)

        self.config = MagicMock(spec=TradingConfig)
        self.config.telegram_token = "fake_token"
        self.config.telegram_chat_id = "fake_chat_id"
        self.config.confidence_threshold = 0.6
        self.config.prometheus_port = 8000

        with patch('prometheus_client.start_http_server'), \
             patch('telegram.Bot'):
            self.monitor = Monitor(self.config)

    def test_log_equity(self):
        self.monitor.metric_equity = MagicMock()
        self.monitor.log_equity(10000.0)
        self.assertEqual(len(self.monitor.equity_history), 1)
        self.assertEqual(self.monitor.equity_history[0]["equity"], 10000.0)
        self.assertIsInstance(self.monitor.equity_history[0]["timestamp"], datetime)
        self.monitor.metric_equity.set.assert_called_with(10000.0)

    def test_log_pnl(self):
        self.monitor.metric_pnl_daily = MagicMock()
        self.monitor.log_pnl(500.0)
        self.monitor.metric_pnl_daily.set.assert_called_with(500.0)

    def test_log_trade(self):
        self.monitor.metric_trades_total = MagicMock()
        self.monitor.log_trade("buy")
        self.monitor.metric_trades_total.labels.assert_called_with(side="buy")
        self.monitor.metric_trades_total.labels().inc.assert_called_once()

    def test_log_error(self):
        self.monitor.metric_errors_total = MagicMock()
        self.monitor.log_error("ConnectionError")
        self.monitor.metric_errors_total.labels.assert_called_with(error_type="ConnectionError")
        self.monitor.metric_errors_total.labels().inc.assert_called_once()

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
        self.assertIn("15.00%", mock_send_message.call_args[0][0])

    @patch('src.core.monitor.Monitor.send_message')
    @patch('src.core.monitor.Monitor.log_pnl')
    def test_send_daily_summary(self, mock_log_pnl, mock_send_message):
        self.monitor.send_daily_summary(500.0, 10)
        mock_log_pnl.assert_called_with(500.0)
        mock_send_message.assert_called_once()
        self.assertIn("Daily Summary", mock_send_message.call_args[0][0])
        self.assertIn("500.00", mock_send_message.call_args[0][0])
        self.assertIn("10", mock_send_message.call_args[0][0])

    @patch('src.core.monitor.Monitor.send_message')
    def test_check_confidence_degradation(self, mock_send_message):
        self.monitor.metric_model_confidence = MagicMock()
        # Case 1: Below threshold
        self.monitor.check_confidence_degradation(0.5)
        self.monitor.metric_model_confidence.set.assert_called_with(0.5)
        mock_send_message.assert_called_once()
        self.assertIn("Confidence Degradation", mock_send_message.call_args[0][0])

        mock_send_message.reset_mock()
        self.monitor.metric_model_confidence.set.reset_mock()

        # Case 2: Above threshold
        self.monitor.check_confidence_degradation(0.7)
        self.monitor.metric_model_confidence.set.assert_called_with(0.7)
        mock_send_message.assert_not_called()

if __name__ == '__main__':
    unittest.main()

"""
Tests for Monitor class.
"""
import unittest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timezone
from src.core.monitor import Monitor
from src.core.config import TradingConfig
import src.core.monitor as monitor_module

class TestMonitor(unittest.TestCase):
    def setUp(self):
        self.config = MagicMock(spec=TradingConfig)
        self.config.telegram_token = "fake_token"
        self.config.telegram_chat_id = "fake_chat_id"
        self.config.confidence_threshold = 0.6
        self.config.prometheus_port = 8000

        with patch('telegram.Bot'), patch('prometheus_client.start_http_server'):
            self.monitor = Monitor(self.config)

    def test_log_equity(self):
        with patch.object(monitor_module.EQUITY_GAUGE, 'set') as mock_set:
            # Test deque behavior
            for i in range(1100):
                self.monitor.log_equity(10000.0 + i)

            self.assertEqual(len(self.monitor.equity_history), 1000)
            self.assertEqual(self.monitor.equity_history[-1]["equity"], 11099.0)
            self.assertIsInstance(self.monitor.equity_history[0]["timestamp"], datetime)
            mock_set.assert_called_with(11099.0)

    @patch('asyncio.run')
    def test_send_message(self, mock_asyncio_run):
        self.monitor.bot = MagicMock()
        self.monitor.bot.send_message = MagicMock()

        self.monitor.send_message("test message")

        mock_asyncio_run.assert_called_once()

    @patch('src.core.monitor.Monitor.send_message')
    def test_alert_circuit_breaker(self, mock_send_message):
        with patch.object(monitor_module.ERROR_COUNTER.labels(error_type="circuit_breaker"), 'inc') as mock_inc:
            self.monitor.alert_circuit_breaker(0.15)
            mock_send_message.assert_called_once()
            self.assertIn("Circuit Breaker", mock_send_message.call_args[0][0])
            self.assertIn("15.00%", mock_send_message.call_args[0][0])
            mock_inc.assert_called_once()

    @patch('src.core.monitor.Monitor.send_message')
    def test_send_daily_summary(self, mock_send_message):
        with patch.object(monitor_module.PNL_GAUGE, 'set') as mock_set:
            self.monitor.send_daily_summary(500.0, 10)
            mock_send_message.assert_called_once()
            self.assertIn("Daily Summary", mock_send_message.call_args[0][0])
            self.assertIn("500.00", mock_send_message.call_args[0][0])
            self.assertIn("10", mock_send_message.call_args[0][0])
            mock_set.assert_called_with(500.0)

    @patch('src.core.monitor.Monitor.send_message')
    def test_check_confidence_degradation(self, mock_send_message):
        with patch.object(monitor_module.CONFIDENCE_GAUGE, 'set') as mock_conf_set, \
             patch.object(monitor_module.ERROR_COUNTER.labels(error_type="confidence_degradation"), 'inc') as mock_err_inc:

            # Case 1: Below threshold
            self.monitor.check_confidence_degradation(0.5)
            mock_send_message.assert_called_once()
            self.assertIn("Confidence Degradation", mock_send_message.call_args[0][0])
            mock_conf_set.assert_called_with(0.5)
            mock_err_inc.assert_called_once()

            mock_send_message.reset_mock()
            mock_conf_set.reset_mock()
            mock_err_inc.reset_mock()

            # Case 2: Above threshold
            self.monitor.check_confidence_degradation(0.7)
            mock_send_message.assert_not_called()
            mock_conf_set.assert_called_with(0.7)
            mock_err_inc.assert_not_called()

    def test_log_trade_executed(self):
        with patch.object(monitor_module.TRADE_COUNTER.labels(side="buy"), 'inc') as mock_inc:
            self.monitor.log_trade_executed("buy")
            mock_inc.assert_called_once()

if __name__ == '__main__':
    unittest.main()

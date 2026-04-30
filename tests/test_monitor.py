"""
Tests for Monitor class.
"""
import unittest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timezone
from src.core.monitor import Monitor
from src.core.config import TradingConfig

class TestMonitor(unittest.TestCase):
    @patch('src.core.monitor.start_http_server')
    def setUp(self, mock_start_http):
        self.config = MagicMock(spec=TradingConfig)
        self.config.telegram_token = "fake_token"
        self.config.telegram_chat_id = "fake_chat_id"
        self.config.confidence_threshold = 0.6
        self.config.prometheus_port = 8000

        with patch('telegram.Bot'):
            self.monitor = Monitor(self.config)

    @patch('src.core.monitor.EQUITY_GAUGE.set')
    def test_log_equity(self, mock_gauge_set):
        self.monitor.log_equity(10000.0)
        self.assertEqual(len(self.monitor.equity_history), 1)
        self.assertEqual(self.monitor.equity_history[0]["equity"], 10000.0)
        self.assertIsInstance(self.monitor.equity_history[0]["timestamp"], datetime)
        mock_gauge_set.assert_called_with(10000.0)

    @patch('asyncio.run')
    def test_send_message(self, mock_asyncio_run):
        self.monitor.bot = MagicMock()
        self.monitor.bot.send_message = MagicMock()

        self.monitor.send_message("test message")

        mock_asyncio_run.assert_called_once()

    @patch('src.core.monitor.DRAWDOWN_GAUGE.set')
    @patch('src.core.monitor.Monitor.send_message')
    def test_alert_circuit_breaker(self, mock_send_message, mock_gauge_set):
        self.monitor.alert_circuit_breaker(0.15)
        mock_send_message.assert_called_once()
        self.assertIn("Circuit Breaker", mock_send_message.call_args[0][0])
        self.assertIn("15.00%", mock_send_message.call_args[0][0])
        mock_gauge_set.assert_called_with(0.15)

    @patch('src.core.monitor.DAILY_PNL_GAUGE.set')
    @patch('src.core.monitor.Monitor.send_message')
    def test_send_daily_summary(self, mock_send_message, mock_gauge_set):
        self.monitor.send_daily_summary(500.0, 10)
        mock_send_message.assert_called_once()
        self.assertIn("Daily Summary", mock_send_message.call_args[0][0])
        self.assertIn("500.00", mock_send_message.call_args[0][0])
        self.assertIn("10", mock_send_message.call_args[0][0])
        mock_gauge_set.assert_called_with(500.0)

    @patch('src.core.monitor.CONFIDENCE_GAUGE.set')
    @patch('src.core.monitor.Monitor.send_message')
    def test_check_confidence_degradation(self, mock_send_message, mock_gauge_set):
        # Case 1: Below threshold
        self.monitor.check_confidence_degradation(0.5)
        mock_send_message.assert_called_once()
        self.assertIn("Confidence Degradation", mock_send_message.call_args[0][0])
        mock_gauge_set.assert_called_with(0.5)

        mock_send_message.reset_mock()
        mock_gauge_set.reset_mock()

        # Case 2: Above threshold
        self.monitor.check_confidence_degradation(0.7)
        mock_send_message.assert_not_called()
        mock_gauge_set.assert_called_with(0.7)

    @patch('src.core.monitor.TRADE_COUNTER.inc')
    def test_log_trade(self, mock_counter_inc):
        self.monitor.log_trade()
        mock_counter_inc.assert_called_once()

    @patch('src.core.monitor.CONFIDENCE_GAUGE.set')
    def test_log_confidence(self, mock_gauge_set):
        self.monitor.log_confidence(0.85)
        mock_gauge_set.assert_called_with(0.85)

if __name__ == '__main__':
    unittest.main()

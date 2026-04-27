"""
Tests for Monitor class.
"""
import unittest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timezone, timedelta
from src.core.monitor import Monitor
from src.core.config import TradingConfig

class TestMonitor(unittest.TestCase):
    def setUp(self):
        self.config = MagicMock(spec=TradingConfig)
        self.config.telegram_token = "fake_token"
        self.config.telegram_chat_id = "fake_chat_id"
        self.config.confidence_threshold = 0.6
        self.config.prometheus_port = 8000

        with patch('telegram.Bot'):
            self.monitor = Monitor(self.config)

    @patch('src.core.monitor.EQUITY_GAUGE')
    @patch('src.core.monitor.DRAWDOWN_GAUGE')
    def test_log_equity(self, mock_drawdown_gauge, mock_equity_gauge):
        self.monitor.log_equity(10000.0, 0.05)
        self.assertEqual(len(self.monitor.equity_history), 1)
        self.assertEqual(self.monitor.equity_history[0]["equity"], 10000.0)
        self.assertIsInstance(self.monitor.equity_history[0]["timestamp"], datetime)
        mock_equity_gauge.set.assert_called_with(10000.0)
        mock_drawdown_gauge.set.assert_called_with(0.05)

    @patch('src.core.monitor.TRADE_COUNTER')
    def test_log_trade(self, mock_trade_counter):
        self.monitor.log_trade("win")
        mock_trade_counter.labels.assert_called_with(status="win")
        mock_trade_counter.labels().inc.assert_called_once()

    @patch('src.core.monitor.ERROR_COUNTER')
    def test_log_error(self, mock_error_counter):
        self.monitor.log_error("order_manager")
        mock_error_counter.labels.assert_called_with(module="order_manager")
        mock_error_counter.labels().inc.assert_called_once()

    @patch('src.core.monitor.start_http_server')
    def test_start_metrics_server(self, mock_start_http_server):
        self.monitor.start_metrics_server()
        mock_start_http_server.assert_called_once_with(8000)

    @patch('asyncio.run')
    def test_send_message(self, mock_asyncio_run):
        self.monitor.bot = MagicMock()
        self.monitor.bot.send_message = MagicMock()

        self.monitor.send_message("test message")

        mock_asyncio_run.assert_called_once()

    @patch('asyncio.run')
    def test_send_message_throttling(self, mock_asyncio_run):
        self.monitor.bot = MagicMock()
        self.monitor.bot.send_message = MagicMock()

        # Reset cooldown for testing
        self.monitor._alert_cooldown = 10

        # First alert should go through
        self.monitor.send_message("alert 1", alert_type="test_alert")
        self.assertEqual(mock_asyncio_run.call_count, 1)

        # Second alert of same type should be throttled
        self.monitor.send_message("alert 2", alert_type="test_alert")
        self.assertEqual(mock_asyncio_run.call_count, 1)

        # Alert of different type should go through
        self.monitor.send_message("alert 3", alert_type="other_alert")
        self.assertEqual(mock_asyncio_run.call_count, 2)

        # Wait for cooldown
        with patch('src.core.monitor.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime.now(timezone.utc) + timedelta(seconds=11)
            self.monitor.send_message("alert 4", alert_type="test_alert")
            self.assertEqual(mock_asyncio_run.call_count, 3)

    @patch('src.core.monitor.Monitor.send_message')
    def test_alert_circuit_breaker(self, mock_send_message):
        self.monitor.alert_circuit_breaker(0.15)
        mock_send_message.assert_called_once()
        args, kwargs = mock_send_message.call_args
        self.assertIn("Circuit Breaker", args[0])
        self.assertIn("15.00%", args[0])
        self.assertEqual(kwargs['alert_type'], "circuit_breaker")

    @patch('src.core.monitor.PNL_GAUGE')
    @patch('src.core.monitor.Monitor.send_message')
    def test_send_daily_summary(self, mock_send_message, mock_pnl_gauge):
        self.monitor.send_daily_summary(500.0, 10)
        mock_send_message.assert_called_once()
        self.assertIn("Daily Summary", mock_send_message.call_args[0][0])
        self.assertIn("500.00", mock_send_message.call_args[0][0])
        self.assertIn("10", mock_send_message.call_args[0][0])
        mock_pnl_gauge.set.assert_called_with(500.0)

    @patch('src.core.monitor.Monitor.send_message')
    def test_check_confidence_degradation(self, mock_send_message):
        # Case 1: Below threshold
        self.monitor.check_confidence_degradation(0.5)
        mock_send_message.assert_called_once()
        args, kwargs = mock_send_message.call_args
        self.assertIn("Confidence Degradation", args[0])
        self.assertEqual(kwargs['alert_type'], "confidence_degradation")

        mock_send_message.reset_mock()

        # Case 2: Above threshold
        self.monitor.check_confidence_degradation(0.7)
        mock_send_message.assert_not_called()

if __name__ == '__main__':
    unittest.main()

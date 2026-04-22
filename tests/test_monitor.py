"""
Tests for Monitor class.
"""
import unittest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timezone
from src.core.monitor import Monitor, trading_equity, trading_pnl_daily, trading_trades_total, trading_errors_total, trading_model_confidence
from src.core.config import TradingConfig

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
        with patch.object(trading_equity, 'set') as mock_set:
            self.monitor.log_equity(10000.0)
            self.assertEqual(len(self.monitor.equity_history), 1)
            self.assertEqual(self.monitor.equity_history[0]["equity"], 10000.0)
            mock_set.assert_called_once_with(10000.0)

    def test_log_trade_executed(self):
        with patch.object(trading_trades_total, 'labels') as mock_labels:
            mock_inc = MagicMock()
            mock_labels.return_value.inc = mock_inc
            self.monitor.log_trade_executed("buy")
            mock_labels.assert_called_once_with(side="buy")
            mock_inc.assert_called_once()

    def test_log_error(self):
        with patch.object(trading_errors_total, 'labels') as mock_labels:
            mock_inc = MagicMock()
            mock_labels.return_value.inc = mock_inc
            self.monitor.log_error("ConnectionError")
            mock_labels.assert_called_once_with(error_type="ConnectionError")
            mock_inc.assert_called_once()

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
    def test_send_daily_summary(self, mock_send_message):
        with patch.object(trading_pnl_daily, 'set') as mock_set:
            self.monitor.send_daily_summary(500.0, 10)
            mock_send_message.assert_called_once()
            self.assertIn("Daily Summary", mock_send_message.call_args[0][0])
            self.assertIn("500.00", mock_send_message.call_args[0][0])
            mock_set.assert_called_once_with(500.0)

    @patch('src.core.monitor.Monitor.send_message')
    def test_check_confidence_degradation(self, mock_send_message):
        with patch.object(trading_model_confidence, 'set') as mock_set:
            # Case 1: Below threshold
            self.monitor.check_confidence_degradation(0.5)
            mock_send_message.assert_called_once()
            self.assertIn("Confidence Degradation", mock_send_message.call_args[0][0])
            mock_set.assert_called_once_with(0.5)

            mock_send_message.reset_mock()
            mock_set.reset_mock()

            # Case 2: Above threshold
            self.monitor.check_confidence_degradation(0.7)
            mock_send_message.assert_not_called()
            mock_set.assert_called_once_with(0.7)

if __name__ == '__main__':
    unittest.main()

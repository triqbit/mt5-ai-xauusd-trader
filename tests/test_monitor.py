"""
Tests for Monitor class.
"""
import unittest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timezone
from src.core.monitor import Monitor
from src.core.config import TradingConfig

class TestMonitor(unittest.TestCase):
    def setUp(self):
        self.config = MagicMock(spec=TradingConfig)
        self.config.telegram_token = "fake_token"
        self.config.telegram_chat_id = "fake_chat_id"
        self.config.confidence_threshold = 0.6
        self.config.prometheus_port = 8000

        # Mocking prometheus_client metrics to avoid actual metric registration during tests
        with patch('prometheus_client.Gauge'), \
             patch('prometheus_client.Counter'), \
             patch('telegram.Bot'):
            self.monitor = Monitor(self.config)

    @patch('src.core.monitor.METRIC_EQUITY')
    @patch('src.core.monitor.METRIC_DRAWDOWN')
    def test_log_equity(self, mock_drawdown, mock_equity):
        self.monitor.log_equity(10000.0, 0.05)
        self.assertEqual(len(self.monitor.equity_history), 1)
        self.assertEqual(self.monitor.equity_history[0]["equity"], 10000.0)
        self.assertIsInstance(self.monitor.equity_history[0]["timestamp"], datetime)
        mock_equity.set.assert_called_with(10000.0)
        mock_drawdown.set.assert_called_with(0.05)

    @patch('src.core.monitor.METRIC_TRADES_TOTAL')
    def test_log_trade(self, mock_trades):
        self.monitor.log_trade("buy", "filled")
        mock_trades.labels.assert_called_with(side="buy", result="filled")
        mock_trades.labels().inc.assert_called_once()

    @patch('src.core.monitor.METRIC_ERRORS_TOTAL')
    def test_log_error(self, mock_errors):
        self.monitor.log_error("connection_lost")
        mock_errors.labels.assert_called_with(type="connection_lost")
        mock_errors.labels().inc.assert_called_once()

    @patch('src.core.monitor.start_http_server')
    def test_start_metrics_server(self, mock_start_server):
        self.monitor.start_metrics_server()
        mock_start_server.assert_called_with(8000)

    @patch('asyncio.run')
    def test_send_message(self, mock_asyncio_run):
        self.monitor.bot = MagicMock()
        self.monitor.bot.send_message = MagicMock()

        self.monitor.send_message("test message")

        mock_asyncio_run.assert_called_once()

    @patch('src.core.monitor.Monitor.send_message')
    @patch('src.core.monitor.METRIC_DRAWDOWN')
    def test_alert_circuit_breaker(self, mock_drawdown, mock_send_message):
        self.monitor.alert_circuit_breaker(0.15)
        mock_send_message.assert_called_once()
        self.assertIn("Circuit Breaker", mock_send_message.call_args[0][0])
        self.assertIn("15.00%", mock_send_message.call_args[0][0])
        mock_drawdown.set.assert_called_with(0.15)

    @patch('src.core.monitor.Monitor.send_message')
    @patch('src.core.monitor.METRIC_PNL_DAILY')
    def test_send_daily_summary(self, mock_pnl, mock_send_message):
        self.monitor.send_daily_summary(500.0, 10)
        mock_send_message.assert_called_once()
        self.assertIn("Daily Summary", mock_send_message.call_args[0][0])
        self.assertIn("500.00", mock_send_message.call_args[0][0])
        self.assertIn("10", mock_send_message.call_args[0][0])
        mock_pnl.set.assert_called_with(500.0)

    @patch('src.core.monitor.Monitor.send_message')
    @patch('src.core.monitor.METRIC_CONFIDENCE')
    def test_check_confidence_degradation(self, mock_confidence, mock_send_message):
        # Case 1: Below threshold
        self.monitor.check_confidence_degradation(0.5)
        mock_send_message.assert_called_once()
        self.assertIn("Confidence Degradation", mock_send_message.call_args[0][0])
        mock_confidence.set.assert_called_with(0.5)

        mock_send_message.reset_mock()

        # Case 2: Above threshold
        self.monitor.check_confidence_degradation(0.7)
        mock_send_message.assert_not_called()
        mock_confidence.set.assert_called_with(0.7)

if __name__ == '__main__':
    unittest.main()

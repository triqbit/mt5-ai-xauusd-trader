"""
Tests for Monitor class.
"""
import unittest
import asyncio
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

        with patch('src.core.monitor.start_http_server'), \
             patch('telegram.Bot'):
            self.monitor = Monitor(self.config)

    @patch('src.core.monitor.EQUITY.set')
    @patch('src.core.monitor.DRAWDOWN.set')
    def test_log_equity(self, mock_dd_set, mock_equity_set):
        self.monitor.log_equity(10000.0, drawdown=0.05)
        self.assertEqual(len(self.monitor.equity_history), 1)
        self.assertEqual(self.monitor.equity_history[0]["equity"], 10000.0)
        self.assertEqual(self.monitor.equity_history[0]["drawdown"], 0.05)

        mock_equity_set.assert_called_with(10000.0)
        mock_dd_set.assert_called_with(0.05)

    @patch('asyncio.run')
    def test_send_message(self, mock_asyncio_run):
        # Setup mock bot for async context manager
        mock_bot = MagicMock()
        mock_bot.__aenter__ = AsyncMock(return_value=mock_bot)
        mock_bot.__aexit__ = AsyncMock(return_value=None)
        mock_bot.send_message = AsyncMock()

        self.monitor.bot = mock_bot

        self.monitor.send_message("test message")

        mock_asyncio_run.assert_called_once()
        # Verify that the coroutine was indeed passed to asyncio.run
        args, kwargs = mock_asyncio_run.call_args
        self.assertTrue(asyncio.iscoroutine(args[0]))
        # We need to close the coroutine to avoid RuntimeWarning
        args[0].close()

    @patch('src.core.monitor.DRAWDOWN.set')
    @patch('src.core.monitor.Monitor.send_message')
    def test_alert_circuit_breaker(self, mock_send_message, mock_dd_set):
        self.monitor.alert_circuit_breaker(0.15)
        mock_send_message.assert_called_once()
        mock_dd_set.assert_called_with(0.15)
        self.assertIn("Circuit Breaker", mock_send_message.call_args[0][0])
        self.assertIn("15.00%", mock_send_message.call_args[0][0])

    @patch('src.core.monitor.DAILY_PNL.set')
    @patch('src.core.monitor.Monitor.send_message')
    def test_send_daily_summary(self, mock_send_message, mock_pnl_set):
        self.monitor.send_daily_summary(500.0, 10)
        mock_send_message.assert_called_once()
        mock_pnl_set.assert_called_with(500.0)
        self.assertIn("Daily Summary", mock_send_message.call_args[0][0])
        self.assertIn("500.00", mock_send_message.call_args[0][0])
        self.assertIn("10", mock_send_message.call_args[0][0])

    @patch('src.core.monitor.MODEL_CONFIDENCE.set')
    @patch('src.core.monitor.Monitor.send_message')
    def test_check_confidence_degradation(self, mock_send_message, mock_conf_set):
        # Case 1: Below threshold
        self.monitor.check_confidence_degradation(0.5)
        mock_send_message.assert_called_once()
        mock_conf_set.assert_called_with(0.5)
        self.assertIn("Confidence Degradation", mock_send_message.call_args[0][0])

        mock_send_message.reset_mock()
        mock_conf_set.reset_mock()

        # Case 2: Above threshold
        self.monitor.check_confidence_degradation(0.7)
        mock_send_message.assert_not_called()
        mock_conf_set.assert_called_with(0.7)

    @patch('src.core.monitor.TRADE_COUNT.inc')
    def test_record_trade(self, mock_trade_inc):
        self.monitor.record_trade()
        mock_trade_inc.assert_called_once()

if __name__ == '__main__':
    unittest.main()

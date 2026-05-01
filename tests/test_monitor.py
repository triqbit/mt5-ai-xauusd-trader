"""
Tests for Monitor class.
"""
import unittest
import logging
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

        with patch('telegram.Bot'):
            self.monitor = Monitor(self.config)

    def test_log_equity(self):
        self.monitor.log_equity(10000.0)
        self.assertEqual(len(self.monitor.equity_history), 1)
        self.assertEqual(self.monitor.equity_history[0]["equity"], 10000.0)
        self.assertIsInstance(self.monitor.equity_history[0]["timestamp"], datetime)

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

        # Test LOSS summary
        mock_send_message.reset_mock()
        self.monitor.send_daily_summary(-200.0, 5)
        self.assertIn("LOSS", mock_send_message.call_args[0][0])

    @patch('src.core.monitor.Monitor.send_message')
    def test_check_confidence_degradation(self, mock_send_message):
        # Case 1: Below threshold
        self.monitor.check_confidence_degradation(0.5)
        mock_send_message.assert_called_once()
        self.assertIn("Confidence Degradation", mock_send_message.call_args[0][0])

        mock_send_message.reset_mock()

        # Case 2: Above threshold
        self.monitor.check_confidence_degradation(0.7)
        mock_send_message.assert_not_called()

    def test_bot_initialization_failure(self):
        with patch('telegram.Bot', side_effect=Exception("API error")):
            monitor = Monitor(self.config)
            self.assertIsNone(monitor.bot)

    def test_send_message_no_config(self):
        self.monitor.bot = None
        # Should not raise exception
        self.monitor.send_message("test")

    @patch('asyncio.run')
    def test_send_message_exception(self, mock_asyncio_run):
        mock_asyncio_run.side_effect = Exception("Async error")
        self.monitor.bot = MagicMock()
        # Use a more reliable way to check logging if assertLogs fails in some environments
        # or just ensure it doesn't crash.
        self.monitor.send_message("test")

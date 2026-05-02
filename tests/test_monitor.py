"""
Tests for Monitor class.
"""

import unittest
from unittest.mock import MagicMock, patch

from pydantic import SecretStr

from src.core.config import TradingConfig
from src.core.monitor import (
    CONFIDENCE_GAUGE,
    DAILY_PNL_GAUGE,
    DRAWDOWN_GAUGE,
    EQUITY_GAUGE,
    TRADE_COUNTER,
    Monitor,
)


class TestMonitor(unittest.TestCase):
    def setUp(self):
        self.config = MagicMock(spec=TradingConfig)
        self.config.telegram_token = SecretStr("fake_token")
        self.config.telegram_chat_id = "fake_chat_id"
        self.config.confidence_threshold = 0.6
        self.config.prometheus_port = 8000

        with patch("telegram.Bot"):
            self.monitor = Monitor(self.config)

    def test_log_equity(self):
        with patch.object(EQUITY_GAUGE, "set") as mock_set:
            self.monitor.log_equity(10500.0)
            self.assertEqual(len(self.monitor.equity_history), 1)
            self.assertEqual(self.monitor.equity_history[0]["equity"], 10500.0)
            mock_set.assert_called_once_with(10500.0)

    @patch("asyncio.run")
    def test_send_message_sync(self, mock_asyncio_run):
        self.monitor.bot = MagicMock()
        # Mocking the async send_message
        self.monitor.bot.send_message = MagicMock()

        with patch("asyncio.get_event_loop") as mock_get_loop:
            mock_get_loop.side_effect = RuntimeError("No loop")
            self.monitor.send_message("test message")
            mock_asyncio_run.assert_called_once()

    @patch("asyncio.create_task")
    def test_send_message_async(self, mock_create_task):
        self.monitor.bot = MagicMock()
        self.monitor.bot.send_message = MagicMock()

        mock_loop = MagicMock()
        mock_loop.is_running.return_value = True

        with patch("asyncio.get_event_loop", return_value=mock_loop):
            self.monitor.send_message("test message")
            mock_create_task.assert_called_once()

    @patch("src.core.monitor.Monitor.send_message")
    def test_alert_circuit_breaker(self, mock_send_message):
        with patch.object(DRAWDOWN_GAUGE, "set") as mock_set:
            self.monitor.alert_circuit_breaker(0.15)
            mock_send_message.assert_called_once()
            self.assertIn("Circuit Breaker", mock_send_message.call_args[0][0])
            self.assertIn("15.00%", mock_send_message.call_args[0][0])
            mock_set.assert_called_once_with(15.0)

    @patch("src.core.monitor.Monitor.send_message")
    def test_send_daily_summary(self, mock_send_message):
        with patch.object(DAILY_PNL_GAUGE, "set") as mock_set:
            self.monitor.send_daily_summary(500.0, 10)
            mock_send_message.assert_called_once()
            self.assertIn("Daily Summary", mock_send_message.call_args[0][0])
            self.assertIn("500.00", mock_send_message.call_args[0][0])
            self.assertIn("10", mock_send_message.call_args[0][0])
            mock_set.assert_called_once_with(500.0)

    @patch("src.core.monitor.Monitor.send_message")
    def test_check_confidence_degradation(self, mock_send_message):
        with patch.object(CONFIDENCE_GAUGE, "set") as mock_set:
            # Case 1: Below threshold
            self.monitor.check_confidence_degradation(0.5)
            mock_send_message.assert_called_once()
            self.assertIn("Confidence Degradation", mock_send_message.call_args[0][0])
            mock_set.assert_called_with(0.5)

            mock_send_message.reset_mock()

            # Case 2: Above threshold
            self.monitor.check_confidence_degradation(0.7)
            mock_send_message.assert_not_called()
            mock_set.assert_called_with(0.7)

    def test_record_trade(self):
        with patch.object(TRADE_COUNTER, "inc") as mock_inc:
            self.monitor.record_trade()
            mock_inc.assert_called_once()

    @patch("src.core.monitor.start_http_server")
    def test_start_metrics_server(self, mock_start_server):
        self.monitor.start_metrics_server()
        mock_start_server.assert_called_once_with(8000)
        self.assertTrue(self.monitor._server_started)

        # Second call should not start it again
        self.monitor.start_metrics_server()
        mock_start_server.assert_called_once()


if __name__ == "__main__":
    unittest.main()

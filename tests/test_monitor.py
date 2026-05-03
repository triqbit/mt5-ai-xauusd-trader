"""
Tests for Monitor class.
"""
import unittest
from unittest.mock import MagicMock, patch

from src.core.config import TradingConfig
from src.core.monitor import (
    CONFIDENCE_GAUGE,
    DAILY_PNL_GAUGE,
    DRAWDOWN_GAUGE,
    EQUITY_GAUGE,
    SHARPE_RATIO_GAUGE,
    SYSTEM_ERROR_COUNTER,
    TRADE_COUNTER,
    WIN_RATE_GAUGE,
    Monitor,
)


class TestMonitor(unittest.TestCase):
    def setUp(self):
        self.config = MagicMock(spec=TradingConfig)
        self.config.telegram_token = "fake_token"
        self.config.telegram_chat_id = "fake_chat_id"
        self.config.confidence_threshold = 0.6
        self.config.prometheus_port = 8000

        with patch('telegram.Bot'):
            self.monitor = Monitor(self.config)

    def test_log_equity(self):
        with patch.object(EQUITY_GAUGE, 'set') as mock_set:
            self.monitor.log_equity(10500.0)
            self.assertEqual(len(self.monitor.equity_history), 1)
            self.assertEqual(self.monitor.equity_history[0]["equity"], 10500.0)
            mock_set.assert_called_once_with(10500.0)

    @patch("asyncio.run")
    @patch("asyncio.get_running_loop")
    def test_send_message_sync(self, mock_get_running_loop, mock_asyncio_run):
        self.monitor.bot = MagicMock()
        # Mocking the async send_message
        self.monitor.bot.send_message = MagicMock()

        mock_get_running_loop.side_effect = RuntimeError("No loop")
        self.monitor.send_message("test message")
        mock_asyncio_run.assert_called_once()

    @patch("asyncio.get_running_loop")
    def test_send_message_async(self, mock_get_running_loop):
        self.monitor.bot = MagicMock()
        self.monitor.bot.send_message = MagicMock()

        mock_loop = MagicMock()
        mock_get_running_loop.return_value = mock_loop

        self.monitor.send_message("test message")
        mock_loop.create_task.assert_called_once()

    @patch('src.core.monitor.Monitor.send_message')
    def test_alert_circuit_breaker(self, mock_send_message):
        with patch.object(DRAWDOWN_GAUGE, 'set') as mock_set:
            self.monitor.alert_circuit_breaker(0.15)
            mock_send_message.assert_called_once()
            self.assertIn("Circuit Breaker", mock_send_message.call_args[0][0])
            self.assertIn("15.00%", mock_send_message.call_args[0][0])
            mock_set.assert_called_once_with(15.0)

    @patch('src.core.monitor.Monitor.send_message')
    def test_send_daily_summary(self, mock_send_message):
        with patch.object(DAILY_PNL_GAUGE, 'set') as mock_set:
            self.monitor.send_daily_summary(500.0, 10)
            mock_send_message.assert_called_once()
            self.assertIn("Daily Summary", mock_send_message.call_args[0][0])
            self.assertIn("500.00", mock_send_message.call_args[0][0])
            self.assertIn("10", mock_send_message.call_args[0][0])
            mock_set.assert_called_once_with(500.0)

    @patch('src.core.monitor.Monitor.send_message')
    def test_check_confidence_degradation(self, mock_send_message):
        with patch.object(CONFIDENCE_GAUGE, 'set') as mock_set:
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

    @patch("src.core.monitor.Monitor.send_message")
    def test_log_system_error(self, mock_send_message):
        with patch.object(SYSTEM_ERROR_COUNTER, "labels") as mock_labels:
            mock_counter = MagicMock()
            mock_labels.return_value = mock_counter

            self.monitor.log_system_error("MT5", "Connection failed")

            mock_labels.assert_called_once_with(component="MT5")
            mock_counter.inc.assert_called_once()
            mock_send_message.assert_called_once()
            self.assertIn("SYSTEM ERROR", mock_send_message.call_args[0][0])
            self.assertIn("MT5", mock_send_message.call_args[0][0])
            self.assertIn("Connection failed", mock_send_message.call_args[0][0])

    def test_update_performance_metrics(self):
        with patch.object(WIN_RATE_GAUGE, "set") as mock_win_set, patch.object(
            SHARPE_RATIO_GAUGE, "set"
        ) as mock_sharpe_set:
            self.monitor.update_performance_metrics(0.65, 2.1)
            mock_win_set.assert_called_once_with(65.0)
            mock_sharpe_set.assert_called_once_with(2.1)

    @patch("src.core.monitor.start_http_server")
    def test_start_metrics_server(self, mock_start_server):
        self.monitor.start_metrics_server()
        mock_start_server.assert_called_once_with(8000)
        self.assertTrue(self.monitor._server_started)

        # Second call should not start it again
        self.monitor.start_metrics_server()
        mock_start_server.assert_called_once()

if __name__ == '__main__':
    unittest.main()

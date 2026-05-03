"""
Tests for Monitor class.
"""
import asyncio
import unittest
from unittest.mock import MagicMock, patch

from src.core.config import TradingConfig
from datetime import datetime, timezone
from src.core.monitor import (
    CONFIDENCE_GAUGE,
    CPU_USAGE_GAUGE,
    DAILY_PNL_GAUGE,
    DATA_FRESHNESS_GAUGE,
    DISK_USAGE_GAUGE,
    DRAWDOWN_GAUGE,
    EQUITY_GAUGE,
    EXECUTION_LATENCY_HISTOGRAM,
    FILL_RATE_GAUGE,
    MEMORY_USAGE_GAUGE,
    MODEL_ACCURACY_GAUGE,
    MODEL_DRIFT_GAUGE,
    REJECTED_ORDER_COUNTER,
    SHARPE_RATIO_GAUGE,
    SLIPPAGE_HISTOGRAM,
    SYSTEM_ERROR_COUNTER,
    TRADE_COUNTER,
    WIN_RATE_GAUGE,
    Monitor,
)


class TestMonitor(unittest.TestCase):
    def setUp(self):
        self.config = MagicMock()
        self.config.telegram_token.get_secret_value.return_value = "fake_token"
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
    @patch("asyncio.get_running_loop")
    def test_start_metrics_server(self, mock_get_loop, mock_start_server):
        mock_loop = MagicMock()
        mock_get_loop.return_value = mock_loop

        self.monitor.start_metrics_server()
        mock_start_server.assert_called_once_with(8000)
        self.assertTrue(self.monitor._server_started)
        mock_loop.create_task.assert_called_once()

        # Second call should not start it again
        self.monitor.start_metrics_server()
        mock_start_server.assert_called_once()

    @patch("psutil.cpu_percent")
    @patch("psutil.virtual_memory")
    @patch("psutil.disk_usage")
    @patch("asyncio.sleep", side_effect=asyncio.CancelledError)
    def test_collect_system_metrics(self, mock_sleep, mock_disk, mock_mem, mock_cpu):
        mock_cpu.return_value = 10.0
        mock_mem.return_value.percent = 50.0
        mock_disk.return_value.percent = 30.0

        with patch.object(CPU_USAGE_GAUGE, "set") as mock_cpu_set, \
             patch.object(MEMORY_USAGE_GAUGE, "set") as mock_mem_set, \
             patch.object(DISK_USAGE_GAUGE, "set") as mock_disk_set:
            try:
                asyncio.run(self.monitor._collect_system_metrics(interval=1))
            except asyncio.CancelledError:
                pass

            mock_cpu_set.assert_called_with(10.0)
            mock_mem_set.assert_called_with(50.0)
            mock_disk_set.assert_called_with(30.0)

    @patch("src.core.monitor.Monitor.send_message")
    def test_alert_balance_mismatch(self, mock_send_message):
        self.monitor.alert_balance_mismatch(10000.0, 9500.0)
        mock_send_message.assert_called_once()
        self.assertIn("Balance Mismatch", mock_send_message.call_args[0][0])
        self.assertIn("5.00%", mock_send_message.call_args[0][0])

    @patch("src.core.monitor.Monitor.send_message")
    def test_alert_margin_call(self, mock_send_message):
        self.monitor.alert_margin_call(50.0)
        mock_send_message.assert_called_once()
        self.assertIn("Margin Call", mock_send_message.call_args[0][0])
        self.assertIn("50.00%", mock_send_message.call_args[0][0])

    def test_log_execution_quality(self):
        with patch.object(EXECUTION_LATENCY_HISTOGRAM, "observe") as mock_latency, \
             patch.object(SLIPPAGE_HISTOGRAM, "observe") as mock_slippage, \
             patch.object(FILL_RATE_GAUGE, "set") as mock_fill:
            self.monitor.log_execution_quality(150.0, 0.5, 0.95)
            mock_latency.assert_called_once_with(0.15)
            mock_slippage.assert_called_once_with(0.5)
            mock_fill.assert_called_once_with(95.0)

    def test_record_rejection(self):
        with patch.object(REJECTED_ORDER_COUNTER, "inc") as mock_inc:
            self.monitor.record_rejection("Test reason")
            mock_inc.assert_called_once()

    def test_log_model_performance(self):
        with patch.object(MODEL_ACCURACY_GAUGE, "set") as mock_acc, \
             patch.object(MODEL_DRIFT_GAUGE, "set") as mock_drift:
            self.monitor.log_model_performance(0.85, 0.05)
            mock_acc.assert_called_once_with(85.0)
            mock_drift.assert_called_once_with(0.05)

    def test_log_data_freshness(self):
        with patch.object(DATA_FRESHNESS_GAUGE, "set") as mock_set:
            now = datetime.now(timezone.utc)
            self.monitor.log_data_freshness(now)
            mock_set.assert_called_once()
            # age should be close to 0
            self.assertLess(mock_set.call_args[0][0], 1.0)

if __name__ == '__main__':
    unittest.main()

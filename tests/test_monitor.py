"""
Tests for Monitor class.
Ensures real-time tracking, metrics updates, and Telegram alerting work as expected.
"""
import asyncio
import contextlib
import time
import unittest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from src.core.monitor import (
    AVG_TRADE_DURATION_GAUGE,
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
    MONTHLY_RETURN_GAUGE,
    PARTIAL_FILL_COUNTER,
    REJECTED_ORDER_COUNTER,
    SHARPE_RATIO_GAUGE,
    SLIPPAGE_HISTOGRAM,
    SYSTEM_ERROR_COUNTER,
    TRADE_COUNTER,
    TRADING_BLOCK_DURATION,
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
        self.config.model_accuracy_floor = 0.5
        self.config.model_drift_threshold = 0.3
        self.config.model_calibration_threshold = 0.25
        self.config.data_freshness_threshold = 300
        self.config.execution_latency_threshold = 1.0

        with patch('telegram.Bot'):
            self.monitor = Monitor(self.config)

    def test_log_equity(self):
        with patch.object(EQUITY_GAUGE, 'set') as mock_set:
            self.monitor.log_equity(10500.0)
            self.assertEqual(len(self.monitor.equity_history), 1)
            self.assertEqual(self.monitor.equity_history[0]["equity"], 10500.0)
            mock_set.assert_called_once_with(10500.0)

    def test_get_equity_curve(self):
        self.monitor.log_equity(10000.0)
        self.monitor.log_equity(10100.0)
        curve = self.monitor.get_equity_curve()
        self.assertEqual(len(curve), 2)
        self.assertEqual(curve[0]["equity"], 10000.0)
        self.assertEqual(curve[1]["equity"], 10100.0)

    def test_log_pnl(self):
        with patch.object(DAILY_PNL_GAUGE, 'set') as mock_set:
            self.monitor.log_pnl(250.0)
            mock_set.assert_called_once_with(250.0)

    def test_log_monthly_return(self):
        with patch.object(MONTHLY_RETURN_GAUGE, 'set') as mock_set:
            self.monitor.log_monthly_return(1500.0)
            mock_set.assert_called_once_with(1500.0)

    def test_log_trade_duration(self):
        with patch.object(AVG_TRADE_DURATION_GAUGE, 'set') as mock_set:
            self.monitor.log_trade_duration(3600.0)
            mock_set.assert_called_once_with(3600.0)

    @patch("asyncio.run")
    @patch("asyncio.get_running_loop")
    def test_send_message_sync(self, mock_get_running_loop, mock_asyncio_run):
        self.monitor.bot = MagicMock()
        self.monitor.bot.send_message = AsyncMock()

        mock_get_running_loop.side_effect = RuntimeError("No loop")
        self.monitor.send_message("test message")
        mock_asyncio_run.assert_called_once()

    @patch("asyncio.get_running_loop")
    def test_send_message_async(self, mock_get_running_loop):
        self.monitor.bot = MagicMock()
        self.monitor.bot.send_message = AsyncMock()

        mock_loop = MagicMock()
        mock_get_running_loop.return_value = mock_loop

        self.monitor.send_message("test message")
        mock_loop.create_task.assert_called_once()

    def test_alert_circuit_breaker(self):
        self.monitor.bot = MagicMock()
        self.monitor.bot.send_message = AsyncMock()
        with patch.object(DRAWDOWN_GAUGE, 'set') as mock_set:
            self.monitor.alert_circuit_breaker(0.15)
            self.assertTrue(self.monitor.bot.send_message.called)
            msg = self.monitor.bot.send_message.call_args[1]["text"]
            self.assertIn("Circuit Breaker", msg)
            self.assertIn("15.00%", msg)
            mock_set.assert_called_once_with(15.0)

    def test_send_daily_summary(self):
        self.monitor.bot = MagicMock()
        self.monitor.bot.send_message = AsyncMock()
        with patch.object(DAILY_PNL_GAUGE, 'set') as mock_set:
            self.monitor.send_daily_summary(500.0, 10)
            self.assertTrue(self.monitor.bot.send_message.called)
            msg = self.monitor.bot.send_message.call_args[1]["text"]
            self.assertIn("Daily Summary", msg)
            self.assertIn("500.00", msg)
            self.assertIn("10", msg)
            mock_set.assert_called_once_with(500.0)

    def test_check_confidence_degradation(self):
        self.monitor.bot = MagicMock()
        self.monitor.bot.send_message = AsyncMock()
        with patch.object(CONFIDENCE_GAUGE, 'set') as mock_set:
            # Case 1: Below threshold
            self.monitor.check_confidence_degradation(0.5)
            self.assertTrue(self.monitor.bot.send_message.called)
            msg = self.monitor.bot.send_message.call_args[1]["text"]
            self.assertIn("Confidence Degradation", msg)
            mock_set.assert_called_with(0.5)

            self.monitor.bot.send_message.reset_mock()

            # Case 2: Above threshold
            self.monitor.check_confidence_degradation(0.7)
            self.assertFalse(self.monitor.bot.send_message.called)
            mock_set.assert_called_with(0.7)

    def test_record_trade(self):
        with patch.object(TRADE_COUNTER, "inc") as mock_inc:
            self.monitor.record_trade()
            mock_inc.assert_called_once()

    def test_log_system_error(self):
        self.monitor.bot = MagicMock()
        self.monitor.bot.send_message = AsyncMock()
        with patch.object(SYSTEM_ERROR_COUNTER, "labels") as mock_labels:
            mock_counter = MagicMock()
            mock_labels.return_value = mock_counter

            self.monitor.log_system_error("MT5", "Connection failed")

            mock_labels.assert_called_once_with(component="MT5")
            mock_counter.inc.assert_called_once()
            self.assertTrue(self.monitor.bot.send_message.called)
            msg = self.monitor.bot.send_message.call_args[1]["text"]
            self.assertIn("SYSTEM ERROR", msg)
            self.assertIn("MT5", msg)
            self.assertIn("Connection failed", msg)

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

    @patch("psutil.cpu_percent")
    @patch("psutil.virtual_memory")
    @patch("psutil.disk_usage")
    @patch("asyncio.sleep", side_effect=asyncio.CancelledError)
    def test_collect_system_metrics(self, mock_sleep, mock_disk, mock_mem, mock_cpu):
        self.monitor.bot = MagicMock()
        mock_cpu.return_value = 10.0
        mock_mem.return_value.percent = 50.0
        mock_disk.return_value.percent = 30.0

        with patch.object(CPU_USAGE_GAUGE, "set") as mock_cpu_set, \
             patch.object(MEMORY_USAGE_GAUGE, "set") as mock_mem_set, \
             patch.object(DISK_USAGE_GAUGE, "set") as mock_disk_set:
            with contextlib.suppress(asyncio.CancelledError):
                asyncio.run(self.monitor._collect_system_metrics(interval=1))

            mock_cpu_set.assert_called_with(10.0)
            mock_mem_set.assert_called_with(50.0)
            mock_disk_set.assert_called_with(30.0)

    def test_alert_balance_mismatch(self):
        self.monitor.bot = MagicMock()
        self.monitor.bot.send_message = AsyncMock()

        self.monitor.alert_balance_mismatch(10000.0, 9500.0)
        self.assertTrue(self.monitor.bot.send_message.called)
        msg = self.monitor.bot.send_message.call_args[1]["text"]
        self.assertIn("Balance Mismatch", msg)
        self.assertIn("5.00%", msg)

    def test_alert_margin_call(self):
        self.monitor.bot = MagicMock()
        self.monitor.bot.send_message = AsyncMock()

        self.monitor.alert_margin_call(50.0)
        self.assertTrue(self.monitor.bot.send_message.called)
        msg = self.monitor.bot.send_message.call_args[1]["text"]
        self.assertIn("Margin Call", msg)
        self.assertIn("50.00%", msg)

    def test_log_execution_quality(self):
        self.monitor.bot = MagicMock()
        self.monitor.bot.send_message = AsyncMock()

        with patch.object(EXECUTION_LATENCY_HISTOGRAM, "observe") as mock_latency, \
             patch.object(SLIPPAGE_HISTOGRAM, "observe") as mock_slippage, \
             patch.object(FILL_RATE_GAUGE, "set") as mock_fill:

            # Case 1: Normal latency
            self.monitor.log_execution_quality(150.0, 0.5, 0.95)
            mock_latency.assert_called_with(0.15)
            mock_slippage.assert_called_with(0.5)
            mock_fill.assert_called_with(95.0)
            self.assertFalse(self.monitor.bot.send_message.called)

            # Case 2: High latency alert
            self.monitor.log_execution_quality(1500.0, 0.5, 0.95)
            mock_latency.assert_called_with(1.5)
            self.assertTrue(self.monitor.bot.send_message.called)
            msg = self.monitor.bot.send_message.call_args[1]["text"]
            self.assertIn("High Execution Latency", msg)
            self.assertIn("1500.00ms", msg)

    def test_record_rejection(self):
        with patch.object(REJECTED_ORDER_COUNTER, "labels") as mock_labels:
            mock_counter = MagicMock()
            mock_labels.return_value = mock_counter

            self.monitor.record_rejection("insufficient_margin")

            mock_labels.assert_called_once_with(reason="insufficient_margin")
            mock_counter.inc.assert_called_once()

    def test_record_partial_fill(self):
        with patch.object(PARTIAL_FILL_COUNTER, "inc") as mock_inc:
            self.monitor.record_partial_fill()
            mock_inc.assert_called_once()

    def test_log_model_performance(self):
        self.monitor.bot = MagicMock()
        self.monitor.bot.send_message = AsyncMock()

        with patch.object(MODEL_ACCURACY_GAUGE, "set") as mock_acc, \
             patch.object(MODEL_DRIFT_GAUGE, "set") as mock_drift:
            # Case 1: Healthy performance
            self.monitor.log_model_performance(0.85, 0.05)
            mock_acc.assert_called_with(85.0)
            mock_drift.assert_called_with(0.05)
            self.assertFalse(self.monitor.bot.send_message.called)

            # Case 2: Accuracy breach
            self.monitor.log_model_performance(0.45, 0.05)
            self.assertTrue(self.monitor.bot.send_message.called)
            msg = self.monitor.bot.send_message.call_args[1]["text"]
            self.assertIn("Accuracy Below Floor", msg)
            self.monitor.bot.send_message.reset_mock()

            # Case 3: Drift breach
            self.monitor.log_model_performance(0.85, 0.4)
            self.assertTrue(self.monitor.bot.send_message.called)
            msg = self.monitor.bot.send_message.call_args[1]["text"]
            self.assertIn("Model Drift Detected", msg)

    def test_log_data_freshness(self):
        self.monitor.bot = MagicMock()
        self.monitor.bot.send_message = AsyncMock()

        with patch.object(DATA_FRESHNESS_GAUGE, "set") as mock_set:
            # Case 1: Fresh data
            now = datetime.now(timezone.utc)
            self.monitor.log_data_freshness(now)
            mock_set.assert_called_with(mock_set.call_args[0][0])
            self.assertLess(mock_set.call_args[0][0], 1.0)
            self.assertFalse(self.monitor.bot.send_message.called)

            # Case 2: Stale data
            stale_time = datetime.now(timezone.utc).timestamp() - 600
            stale_dt = datetime.fromtimestamp(stale_time, tz=timezone.utc)
            self.monitor.log_data_freshness(stale_dt)
            self.assertTrue(self.monitor.bot.send_message.called)
            msg = self.monitor.bot.send_message.call_args[1]["text"]
            self.assertIn("Data Stale", msg)

    def test_track_block_duration(self):
        with patch.object(TRADING_BLOCK_DURATION, "labels") as mock_labels:
            mock_hist = MagicMock()
            mock_labels.return_value = mock_hist

            with self.monitor.track_block_duration("test_block"):
                time.sleep(0.1)

            mock_labels.assert_called_once_with(block_label="test_block")
            mock_hist.observe.assert_called_once()
            duration = mock_hist.observe.call_args[0][0]
            self.assertGreaterEqual(duration, 0.1)

    def test_alert_liquidity_crisis(self):
        self.monitor.bot = MagicMock()
        self.monitor.bot.send_message = AsyncMock()
        self.monitor.alert_liquidity_crisis("XAUUSD", 2.5)
        self.assertTrue(self.monitor.bot.send_message.called)
        msg = self.monitor.bot.send_message.call_args[1]["text"]
        self.assertIn("Liquidity Crisis", msg)
        self.assertIn("2.50 pips", msg)

    def test_alert_broker_connection_lost(self):
        self.monitor.bot = MagicMock()
        self.monitor.bot.send_message = AsyncMock()
        self.monitor.alert_broker_connection_lost()
        self.assertTrue(self.monitor.bot.send_message.called)
        msg = self.monitor.bot.send_message.call_args[1]["text"]
        self.assertIn("Broker Connection Lost", msg)

    def test_alert_broker_connection_restored(self):
        self.monitor.bot = MagicMock()
        self.monitor.bot.send_message = AsyncMock()
        self.monitor.alert_broker_connection_restored()
        self.assertTrue(self.monitor.bot.send_message.called)
        msg = self.monitor.bot.send_message.call_args[1]["text"]
        self.assertIn("Broker Connection Restored", msg)

    def test_alert_inference_timeout(self):
        self.monitor.bot = MagicMock()
        self.monitor.bot.send_message = AsyncMock()
        self.monitor.alert_inference_timeout(150.0, 100.0)
        self.assertTrue(self.monitor.bot.send_message.called)
        msg = self.monitor.bot.send_message.call_args[1]["text"]
        self.assertIn("Inference Timeout", msg)

    def test_alert_feature_missing(self):
        self.monitor.bot = MagicMock()
        self.monitor.bot.send_message = AsyncMock()
        self.monitor.alert_feature_missing("RSI")
        self.assertTrue(self.monitor.bot.send_message.called)
        msg = self.monitor.bot.send_message.call_args[1]["text"]
        self.assertIn("Missing Model Feature", msg)
        self.assertIn("RSI", msg)

    def test_alert_stale_model(self):
        self.monitor.bot = MagicMock()
        self.monitor.bot.send_message = AsyncMock()
        self.monitor.alert_stale_model(8.5)
        self.assertTrue(self.monitor.bot.send_message.called)
        msg = self.monitor.bot.send_message.call_args[1]["text"]
        self.assertIn("Stale Model Detected", msg)
        self.assertIn("8.5 days", msg)

    def test_alert_training_failed(self):
        self.monitor.bot = MagicMock()
        self.monitor.bot.send_message = AsyncMock()
        self.monitor.alert_training_failed("Disk full")
        self.assertTrue(self.monitor.bot.send_message.called)
        msg = self.monitor.bot.send_message.call_args[1]["text"]
        self.assertIn("Model Retraining Failed", msg)
        self.assertIn("Disk full", msg)

if __name__ == '__main__':
    unittest.main()

"""
Tests for iteration summary logging and telemetry.
"""

import unittest
from unittest.mock import MagicMock, patch

from src.core.monitor import Monitor


class TestIterationSummary(unittest.TestCase):
    def setUp(self):
        self.config = MagicMock()
        self.config.telegram_token.get_secret_value.return_value = "fake_token"
        self.config.telegram_chat_id = "fake_chat_id"
        with patch("telegram.Bot"):
            self.monitor = Monitor(self.config)

    def test_monitor_new_methods(self):
        """Test the newly added recording methods in Monitor."""
        with (
            patch("src.core.monitor.MARKET_STABILITY_GAUGE.set") as mock_stability,
            patch(
                "src.core.monitor.ITERATION_HEARTBEAT_GAUGE.set_to_current_time"
            ) as mock_heartbeat,
            patch("src.core.monitor.ITERATION_DURATION_HISTOGRAM.observe") as mock_duration,
        ):
            self.monitor.record_market_stability(0.85)
            mock_stability.assert_called_once_with(0.85)

            self.monitor.record_iteration_heartbeat()
            mock_heartbeat.assert_called_once()

            self.monitor.record_iteration_duration(1.23)
            mock_duration.assert_called_once_with(1.23)

    def test_send_message_with_trace_id(self):
        """Test that trace_id is appended to Telegram messages."""
        self.monitor.bot = MagicMock()

        # Case 1: With trace_id
        with patch(
            "structlog.contextvars.get_contextvars", return_value={"trace_id": "test-uuid-12345"}
        ):
            self.monitor.send_message("Alert message")
            msg = self.monitor.bot.send_message.call_args[1]["text"]
            self.assertIn("Alert message", msg)
            self.assertIn("[Trace: test-uui]", msg)

        self.monitor.bot.send_message.reset_mock()

        # Case 2: Without trace_id
        with patch("structlog.contextvars.get_contextvars", return_value={}):
            self.monitor.send_message("Alert message")
            msg = self.monitor.bot.send_message.call_args[1]["text"]
            self.assertEqual("Alert message", msg)


if __name__ == "__main__":
    unittest.main()

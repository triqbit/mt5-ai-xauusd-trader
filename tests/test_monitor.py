"""Tests for Monitor class."""

from __future__ import annotations

import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch

from src.core.config import TradingConfig
from src.core.monitor import Monitor


class TestMonitor(unittest.TestCase):
    """Test suite for the Monitor class."""

    def setUp(self) -> None:
        """Set up a mock configuration and Monitor instance for each test."""
        self.config = MagicMock(spec=TradingConfig)
        self.config.telegram_token = "fake_token"
        self.config.telegram_chat_id = "fake_chat_id"
        self.config.confidence_threshold = 0.6

        with patch("telegram.Bot"):
            self.monitor = Monitor(self.config)

    def test_log_equity(self) -> None:
        """Test that equity is correctly logged with a timestamp."""
        self.monitor.log_equity(10000.0)
        assert len(self.monitor.equity_history) == 1
        assert self.monitor.equity_history[0]["equity"] == 10000.0
        assert isinstance(self.monitor.equity_history[0]["timestamp"], datetime)

    @patch("asyncio.run")
    def test_send_message(self, mock_asyncio_run: MagicMock) -> None:
        """Test that sending a message correctly calls the underlying async bot method."""
        self.monitor.bot = MagicMock()
        self.monitor.bot.send_message = MagicMock()

        self.monitor.send_message("Test message")

        mock_asyncio_run.assert_called_once()

    @patch("src.core.monitor.Monitor.send_message")
    def test_alert_circuit_breaker(self, mock_send_message: MagicMock) -> None:
        """Test that circuit breaker alerts contain expected information."""
        self.monitor.alert_circuit_breaker(0.15)
        mock_send_message.assert_called_once()
        assert "Circuit Breaker" in mock_send_message.call_args[0][0]
        assert "15.00%" in mock_send_message.call_args[0][0]

    @patch("src.core.monitor.Monitor.send_message")
    def test_send_daily_summary(self, mock_send_message: MagicMock) -> None:
        """Test that daily summary messages contain PnL and trade count."""
        self.monitor.send_daily_summary(500.0, 10)
        mock_send_message.assert_called_once()
        assert "Daily Summary" in mock_send_message.call_args[0][0]
        assert "500.00" in mock_send_message.call_args[0][0]
        assert "10" in mock_send_message.call_args[0][0]

    @patch("src.core.monitor.Monitor.send_message")
    def test_check_confidence_degradation(self, mock_send_message: MagicMock) -> None:
        """Test that confidence degradation warnings are triggered correctly."""
        # Case 1: Below threshold
        self.monitor.check_confidence_degradation(0.5)
        mock_send_message.assert_called_once()
        assert "Confidence Degradation" in mock_send_message.call_args[0][0]

        mock_send_message.reset_mock()

        # Case 2: Above threshold
        self.monitor.check_confidence_degradation(0.7)
        mock_send_message.assert_not_called()

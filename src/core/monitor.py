"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/core/monitor.py
Real-time monitoring, equity tracking, and Telegram alerting.
Author : triqbit
License: MIT
"""
from __future__ import annotations

import asyncio
import logging
import time
from collections import deque
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import telegram
from prometheus_client import Gauge, start_http_server

from src.core.config import TradingConfig

logger = logging.getLogger(__name__)


class Monitor:
    """
    Real-time monitoring and alerting system.

    Provides real-time equity curve tracking using a deque, Prometheus metrics
    integration, and Telegram alerting with throttling to prevent spam.
    """

    def __init__(self, config: TradingConfig) -> None:
        """
        Initialize the monitor.

        Args:
            config: Trading configuration object.
        """
        self.cfg = config
        self.equity_history: deque[Dict[str, Any]] = deque(maxlen=1000)
        self.bot: Optional[telegram.Bot] = None
        self._last_alert_time: Dict[str, float] = {}
        self._alert_cooldown = 3600  # 1 hour cooldown for same alert type by default

        if self.cfg.telegram_token:
            try:
                self.bot = telegram.Bot(token=self.cfg.telegram_token)
                logger.info("Telegram bot initialized")
            except Exception as e:
                logger.error("Failed to initialize Telegram bot: %s", e)

        # Initialize Prometheus metrics
        self.metric_equity = Gauge("trading_equity", "Current account equity")
        self.metric_daily_pnl = Gauge("trading_daily_pnl", "Daily realized PnL")
        self.metric_confidence = Gauge("model_confidence", "Latest model prediction confidence")

        self._start_prometheus()

    def _start_prometheus(self) -> None:
        """Start the Prometheus HTTP server."""
        try:
            start_http_server(self.cfg.prometheus_port)
            logger.info("Prometheus metrics server started on port %d", self.cfg.prometheus_port)
        except Exception as e:
            logger.error("Failed to start Prometheus server: %s", e)

    def log_equity(self, equity: float) -> None:
        """
        Record current equity with timestamp and update Prometheus metric.

        Args:
            equity: Current account equity.
        """
        data = {"timestamp": datetime.now(timezone.utc), "equity": equity}
        self.equity_history.append(data)
        self.metric_equity.set(equity)
        logger.debug("Equity logged: %.2f", equity)

    def send_message(self, text: str, alert_type: Optional[str] = None) -> None:
        """
        Synchronous wrapper to send Telegram message with optional throttling.

        Args:
            text: Message content.
            alert_type: Key for throttling. If None, no throttling is applied.
        """
        if not self.bot or not self.cfg.telegram_chat_id:
            logger.debug("Telegram bot not configured, message not sent: %s", text)
            return

        now = time.time()
        if alert_type:
            last_time = self._last_alert_time.get(alert_type, 0)
            if now - last_time < self._alert_cooldown:
                logger.debug("Alert '%s' throttled", alert_type)
                return
            self._last_alert_time[alert_type] = now

        try:
            # python-telegram-bot v20+ is async.
            # We use asyncio.run as the main loop is synchronous.
            # Note: In a production environment, you might want a background worker/thread.
            asyncio.run(self.bot.send_message(chat_id=self.cfg.telegram_chat_id, text=text))
            logger.info("Telegram message sent: %s", alert_type or "Generic")
        except Exception as e:
            logger.error("Failed to send Telegram message: %s", e)

    def alert_circuit_breaker(self, drawdown: float) -> None:
        """
        Send critical alert for circuit breaker trigger.

        Args:
            drawdown: Current drawdown fraction.
        """
        msg = f"🚨 CRITICAL: Circuit Breaker Triggered!\nDrawdown: {drawdown*100:.2f}%\nTrading Halted."
        self.send_message(msg, alert_type="circuit_breaker")

    def send_daily_summary(self, pnl: float, trades: int) -> None:
        """
        Send daily P&L and trade count summary and update Prometheus metric.

        Args:
            pnl: Realized P&L for the day.
            trades: Number of trades executed during the day.
        """
        self.metric_daily_pnl.set(pnl)
        status = "PROFIT" if pnl >= 0 else "LOSS"
        msg = (
            f"📅 Daily Summary - {datetime.now(timezone.utc).date()}\n"
            f"Status: {status}\n"
            f"Net P&L: {pnl:.2f}\n"
            f"Trades: {trades}"
        )
        self.send_message(msg)  # Daily summaries are usually triggered once, no throttling needed

    def check_confidence_degradation(self, confidence: float) -> None:
        """
        Send warning if model confidence falls below threshold and update Prometheus metric.

        Args:
            confidence: Current model confidence score.
        """
        self.metric_confidence.set(confidence)
        if confidence < self.cfg.confidence_threshold:
            msg = (
                f"⚠️ WARNING: Model Confidence Degradation\n"
                f"Current: {confidence:.3f}\n"
                f"Threshold: {self.cfg.confidence_threshold:.3f}"
            )
            self.send_message(msg, alert_type="confidence_degradation")


__all__ = ["Monitor"]

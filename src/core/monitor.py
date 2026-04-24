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
from collections import deque
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import telegram
from prometheus_client import Counter, Gauge, start_http_server

from src.core.config import TradingConfig

logger = logging.getLogger(__name__)

# Prometheus Metrics
trading_equity = Gauge("trading_equity", "Current account equity")
trading_pnl_daily = Gauge("trading_pnl_daily", "Daily realised PnL")
trading_trades_total = Counter("trading_trades_total", "Total trades executed", ["side"])
trading_errors_total = Counter("trading_errors_total", "Total errors by type", ["error_type"])
trading_model_confidence = Gauge("trading_model_confidence", "Current model prediction confidence")


class Monitor:
    """
    Real-time monitoring and alerting system.
    Tracks equity curve, updates Prometheus metrics, and sends alerts via Telegram.
    """

    def __init__(self, config: TradingConfig) -> None:
        self.cfg = config
        self.equity_history: deque[Dict[str, Any]] = deque(maxlen=1000)
        self.bot: Optional[telegram.Bot] = None
        self._last_confidence_alert: Optional[datetime] = None

        if self.cfg.telegram_token:
            try:
                self.bot = telegram.Bot(token=self.cfg.telegram_token)
                logger.info("Telegram bot initialized")
            except Exception as e:
                logger.error("Failed to initialize Telegram bot: %s", e)

        # Start Prometheus HTTP server
        try:
            start_http_server(self.cfg.prometheus_port)
            logger.info("Prometheus metrics server started on port %d", self.cfg.prometheus_port)
        except Exception as e:
            logger.error("Failed to start Prometheus server: %s", e)

    def log_equity(self, equity: float) -> None:
        """Record current equity with timestamp and update Prometheus."""
        data = {"timestamp": datetime.now(timezone.utc), "equity": equity}
        self.equity_history.append(data)
        trading_equity.set(equity)
        logger.debug("Equity logged: %.2f", equity)

    def log_trade(self, side: str, lot_size: float) -> None:
        """Update trade counter metrics."""
        trading_trades_total.labels(side=side).inc()
        logger.info("Trade logged in monitor: side=%s, lots=%.2f", side, lot_size)

    def log_error(self, error_type: str) -> None:
        """Update error counter metrics."""
        trading_errors_total.labels(error_type=error_type).inc()
        logger.error("Error logged in monitor: type=%s", error_type)

    def send_message(self, text: str) -> None:
        """Synchronous wrapper to send Telegram message."""
        if not self.bot or not self.cfg.telegram_chat_id:
            logger.debug("Telegram bot not configured, message not sent: %s", text)
            return

        try:
            # python-telegram-bot v20+ is async.
            # We use asyncio.run as the main loop is synchronous.
            asyncio.run(self.bot.send_message(chat_id=self.cfg.telegram_chat_id, text=text))
            logger.info("Telegram message sent")
        except Exception as e:
            logger.error("Failed to send Telegram message: %s", e)

    def alert_circuit_breaker(self, drawdown: float) -> None:
        """Send critical alert for circuit breaker trigger."""
        msg = f"🚨 CRITICAL: Circuit Breaker Triggered!\nDrawdown: {drawdown*100:.2f}%\nTrading Halted."
        self.send_message(msg)

    def send_daily_summary(self, pnl: float, trades: int) -> None:
        """Send daily P&L and trade count summary and update Prometheus."""
        trading_pnl_daily.set(pnl)
        status = "PROFIT" if pnl >= 0 else "LOSS"
        msg = (
            f"📅 Daily Summary - {datetime.now(timezone.utc).date()}\n"
            f"Status: {status}\n"
            f"Net P&L: {pnl:.2f}\n"
            f"Trades: {trades}"
        )
        self.send_message(msg)

    def check_confidence_degradation(self, confidence: float) -> None:
        """
        Send warning if model confidence falls below threshold.
        Includes a 1-hour cooldown for Telegram alerts.
        """
        trading_model_confidence.set(confidence)
        if confidence < self.cfg.confidence_threshold:
            now = datetime.now(timezone.utc)
            if self._last_confidence_alert is None or (now - self._last_confidence_alert) > timedelta(hours=1):
                msg = (
                    f"⚠️ WARNING: Model Confidence Degradation\n"
                    f"Current: {confidence:.3f}\n"
                    f"Threshold: {self.cfg.confidence_threshold:.3f}"
                )
                self.send_message(msg)
                self._last_confidence_alert = now
            else:
                logger.debug("Confidence alert throttled. Last alert was at %s", self._last_confidence_alert)


__all__ = ["Monitor"]

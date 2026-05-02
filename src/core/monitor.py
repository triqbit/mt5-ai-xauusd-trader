"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/core/monitor.py
Real-time monitoring, equity tracking, Prometheus metrics, and Telegram alerting.
Author : triqbit
License: MIT
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import telegram
from prometheus_client import Counter, Gauge, start_http_server

from src.core.config import TradingConfig

logger = logging.getLogger(__name__)

# --- Prometheus Metrics Definitions ---
EQUITY_GAUGE = Gauge("trading_equity", "Current account equity")
DAILY_PNL_GAUGE = Gauge("trading_pnl_daily", "Realized P&L for the current day")
TRADE_COUNTER = Counter("trading_trades_total", "Total number of trades executed")
DRAWDOWN_GAUGE = Gauge("trading_drawdown_percent", "Current account drawdown percentage")
CONFIDENCE_GAUGE = Gauge("trading_model_confidence", "Latest model prediction confidence")


class Monitor:
    """
    Real-time monitoring and alerting system.
    Tracks equity curve, updates Prometheus metrics, and sends alerts via Telegram.
    """

    def __init__(self, config: TradingConfig) -> None:
        self.cfg = config
        self.equity_history: List[Dict[str, Any]] = []
        self.bot: Optional[telegram.Bot] = None
        self._server_started = False
        self._background_tasks: set[asyncio.Task] = set()

        if self.cfg.telegram_token:
            try:
                self.bot = telegram.Bot(token=self.cfg.telegram_token)
                logger.info("Telegram bot initialized")
            except Exception as e:
                logger.error("Failed to initialize Telegram bot: %s", e)

    def start_metrics_server(self) -> None:
        """Start the Prometheus metrics server if not already running."""
        if self._server_started:
            return
        try:
            start_http_server(self.cfg.prometheus_port)
            self._server_started = True
            logger.info("Prometheus metrics server started on port %d", self.cfg.prometheus_port)
        except Exception as e:
            logger.error("Failed to start Prometheus metrics server: %s", e)

    def log_equity(self, equity: float) -> None:
        """Record current equity and update Prometheus metrics."""
        data = {"timestamp": datetime.now(timezone.utc), "equity": equity}
        self.equity_history.append(data)
        EQUITY_GAUGE.set(equity)
        logger.debug("Equity logged: %.2f", equity)

    def send_message(self, text: str) -> None:
        """Synchronous wrapper to send Telegram message."""
        if not self.bot or not self.cfg.telegram_chat_id:
            logger.debug("Telegram bot not configured, message not sent: %s", text)
            return

        try:
            # python-telegram-bot v20+ is async.
            # We use asyncio.run as the main loop is synchronous.
            # Note: In production, we should handle if there's already a running loop.
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = None

            if loop and loop.is_running():
                # If we are in an async context, we shouldn't use asyncio.run
                # But main.py is mostly synchronous.
                # A safer way to do this in a multi-threaded/async environment
                # is to have a dedicated worker for Telegram messages.
                # For now, adhering to the requested implementation.
                task = asyncio.create_task(
                    self.bot.send_message(chat_id=self.cfg.telegram_chat_id, text=text)
                )
                # Store task reference to prevent garbage collection (RUF006)
                self._background_tasks.add(task)
                task.add_done_callback(self._background_tasks.discard)
            else:
                asyncio.run(self.bot.send_message(chat_id=self.cfg.telegram_chat_id, text=text))

            logger.info("Telegram message sent")
        except Exception as e:
            logger.error("Failed to send Telegram message: %s", e)

    def alert_circuit_breaker(self, drawdown: float) -> None:
        """Send critical alert for circuit breaker trigger and update metrics."""
        DRAWDOWN_GAUGE.set(drawdown * 100)
        msg = f"🚨 CRITICAL: Circuit Breaker Triggered!\nDrawdown: {drawdown * 100:.2f}%\nTrading Halted."
        self.send_message(msg)

    def send_daily_summary(self, pnl: float, trades: int) -> None:
        """Send daily P&L and trade count summary and update metrics."""
        DAILY_PNL_GAUGE.set(pnl)
        # Note: TRADE_COUNTER is cumulative, so we don't set it to 'trades' directly here
        # unless 'trades' is the increment.
        status = "PROFIT" if pnl >= 0 else "LOSS"
        msg = (
            f"📅 Daily Summary - {datetime.now(timezone.utc).date()}\n"
            f"Status: {status}\n"
            f"Net P&L: {pnl:.2f}\n"
            f"Trades Today: {trades}"
        )
        self.send_message(msg)

    def check_confidence_degradation(self, confidence: float) -> None:
        """Send warning if model confidence falls below threshold and update metrics."""
        CONFIDENCE_GAUGE.set(confidence)
        if confidence < self.cfg.confidence_threshold:
            msg = (
                f"⚠️ WARNING: Model Confidence Degradation\n"
                f"Current: {confidence:.3f}\n"
                f"Threshold: {self.cfg.confidence_threshold:.3f}"
            )
            self.send_message(msg)

    def record_trade(self) -> None:
        """Increment the total trade counter."""
        TRADE_COUNTER.inc()


__all__ = ["Monitor"]

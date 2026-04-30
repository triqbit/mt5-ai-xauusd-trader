"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/core/monitor.py
Real-time monitoring, equity tracking, and Telegram alerting with Prometheus metrics.
Author : triqbit
License: MIT
"""

from __future__ import annotations

import asyncio
import logging
from collections import deque
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import telegram
from prometheus_client import Counter, Gauge, start_http_server

from src.core.config import TradingConfig

logger = logging.getLogger(__name__)

# Prometheus Metrics
EQUITY = Gauge("trading_equity", "Current account equity")
DRAWDOWN = Gauge("trading_drawdown_pct", "Current peak-to-trough drawdown percentage")
DAILY_PNL = Gauge("trading_daily_pnl", "Realised PnL for the current trading day")
TRADE_COUNT = Counter("trading_trades_total", "Total number of trades executed")
MODEL_CONFIDENCE = Gauge("trading_model_confidence", "Latest model prediction confidence")


class Monitor:
    """
    Real-time monitoring and alerting system.
    Tracks equity curve, updates Prometheus metrics, and sends alerts via Telegram.
    """

    def __init__(self, config: TradingConfig) -> None:
        self.cfg = config
        # Use deque with maxlen to prevent memory bloat
        self.equity_history: deque[Dict[str, Any]] = deque(maxlen=10000)
        self.bot: Optional[telegram.Bot] = None

        # Start Prometheus Metrics Server
        try:
            start_http_server(self.cfg.prometheus_port)
            logger.info("Prometheus metrics server started on port %d", self.cfg.prometheus_port)
        except Exception as e:
            logger.error("Failed to start Prometheus server: %s", e)

        # Initialize Telegram Bot
        if self.cfg.telegram_token:
            try:
                self.bot = telegram.Bot(token=self.cfg.telegram_token)
                logger.info("Telegram bot initialized")
            except Exception as e:
                logger.error("Failed to initialize Telegram bot: %s", e)

    def log_equity(self, equity: float, drawdown: float = 0.0) -> None:
        """
        Record current equity and drawdown.
        Updates Prometheus gauges and internal history.
        """
        data = {
            "timestamp": datetime.now(timezone.utc),
            "equity": equity,
            "drawdown": drawdown,
        }
        self.equity_history.append(data)

        # Update Prometheus
        EQUITY.set(equity)
        DRAWDOWN.set(drawdown)

        logger.debug("Equity logged: %.2f (DD: %.2f%%)", equity, drawdown * 100)

    def send_message(self, text: str) -> None:
        """
        Synchronous wrapper to send Telegram message.
        Uses asyncio.run to execute the async send_message call.
        """
        if not self.bot or not self.cfg.telegram_chat_id:
            logger.debug("Telegram bot not configured, message not sent: %s", text)
            return

        async def _send():
            async with self.bot:
                await self.bot.send_message(chat_id=self.cfg.telegram_chat_id, text=text)

        try:
            # We use asyncio.run as the main loop is synchronous.
            # Note: This will fail if an event loop is already running in the current thread.
            asyncio.run(_send())
            logger.info("Telegram message sent")
        except Exception as e:
            logger.error("Failed to send Telegram message: %s", e)

    def alert_circuit_breaker(self, drawdown: float) -> None:
        """
        Send critical alert for circuit breaker trigger and update Prometheus.
        """
        DRAWDOWN.set(drawdown)
        msg = f"🚨 CRITICAL: Circuit Breaker Triggered!\nDrawdown: {drawdown * 100:.2f}%\nTrading Halted."
        self.send_message(msg)

    def send_daily_summary(self, pnl: float, trades: int) -> None:
        """
        Send daily P&L and trade count summary and update Prometheus.
        """
        DAILY_PNL.set(pnl)

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
        Update model confidence metric and send warning if below threshold.
        """
        MODEL_CONFIDENCE.set(confidence)

        if confidence < self.cfg.confidence_threshold:
            msg = (
                f"⚠️ WARNING: Model Confidence Degradation\n"
                f"Current: {confidence:.3f}\n"
                f"Threshold: {self.cfg.confidence_threshold:.3f}"
            )
            self.send_message(msg)
            logger.warning("Model confidence degradation detected: %.3f", confidence)

    def record_trade(self) -> None:
        """Increment trade counter metric."""
        TRADE_COUNT.inc()


__all__ = ["Monitor"]

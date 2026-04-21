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
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import telegram
from prometheus_client import Counter, Gauge, start_http_server

from src.core.config import TradingConfig

logger = logging.getLogger(__name__)

# Prometheus Metrics Definitions
EQUITY_GAUGE = Gauge("trading_equity", "Current account equity")
PNL_GAUGE = Gauge("trading_pnl_daily", "Realised daily P&L")
TRADE_COUNTER = Counter("trading_trades_total", "Total trades executed", ["side"])
ERROR_COUNTER = Counter("trading_errors_total", "Total errors encountered", ["error_type"])
CONFIDENCE_GAUGE = Gauge("trading_model_confidence", "Current model prediction confidence")


class Monitor:
    """
    Real-time monitoring and alerting system.
    Tracks equity curve and sends alerts via Telegram.
    Includes Prometheus metrics for Grafana visualization.
    """

    def __init__(self, config: TradingConfig) -> None:
        self.cfg = config
        self.equity_history: deque[Dict[str, Any]] = deque(maxlen=1000)
        self.bot: Optional[telegram.Bot] = None

        # Start Prometheus Metrics Server
        try:
            start_http_server(self.cfg.prometheus_port)
            logger.info("Prometheus metrics server started on port %d", self.cfg.prometheus_port)
        except Exception as e:
            logger.error("Failed to start Prometheus server: %s", e)

        if self.cfg.telegram_token:
            try:
                self.bot = telegram.Bot(token=self.cfg.telegram_token)
                logger.info("Telegram bot initialized")
            except Exception as e:
                logger.error("Failed to initialize Telegram bot: %s", e)

    def log_equity(self, equity: float) -> None:
        """Record current equity with timestamp and update Prometheus."""
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
            asyncio.run(self.bot.send_message(chat_id=self.cfg.telegram_chat_id, text=text))
            logger.info("Telegram message sent")
        except Exception as e:
            logger.error("Failed to send Telegram message: %s", e)
            ERROR_COUNTER.labels(error_type="telegram_failure").inc()

    def alert_circuit_breaker(self, drawdown: float) -> None:
        """Send critical alert for circuit breaker trigger."""
        msg = f"🚨 CRITICAL: Circuit Breaker Triggered!\nDrawdown: {drawdown*100:.2f}%\nTrading Halted."
        self.send_message(msg)
        ERROR_COUNTER.labels(error_type="circuit_breaker").inc()

    def send_daily_summary(self, pnl: float, trades: int) -> None:
        """Send daily P&L and trade count summary and update Prometheus."""
        status = "PROFIT" if pnl >= 0 else "LOSS"
        msg = (
            f"📅 Daily Summary - {datetime.now(timezone.utc).date()}\n"
            f"Status: {status}\n"
            f"Net P&L: {pnl:.2f}\n"
            f"Trades: {trades}"
        )
        self.send_message(msg)
        PNL_GAUGE.set(pnl)

    def check_confidence_degradation(self, confidence: float) -> None:
        """Send warning if model confidence falls below threshold and update Prometheus."""
        CONFIDENCE_GAUGE.set(confidence)
        if confidence < self.cfg.confidence_threshold:
            msg = (
                f"⚠️ WARNING: Model Confidence Degradation\n"
                f"Current: {confidence:.3f}\n"
                f"Threshold: {self.cfg.confidence_threshold:.3f}"
            )
            self.send_message(msg)
            ERROR_COUNTER.labels(error_type="confidence_degradation").inc()

    def log_trade_executed(self, side: str) -> None:
        """Increment trade counter for Prometheus."""
        TRADE_COUNTER.labels(side=side).inc()


__all__ = ["Monitor"]

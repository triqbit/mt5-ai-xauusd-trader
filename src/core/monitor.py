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
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import telegram
from prometheus_client import Counter, Gauge, start_http_server

from src.core.config import TradingConfig

logger = logging.getLogger(__name__)

# Prometheus Metrics Definitions
METRIC_EQUITY = Gauge("trading_equity", "Current account equity")
METRIC_PNL_DAILY = Gauge("trading_pnl_daily", "Daily net P&L")
METRIC_DRAWDOWN = Gauge("trading_drawdown", "Current account drawdown percentage")
METRIC_TRADES_TOTAL = Counter("trading_trades_total", "Total trades executed", ["side", "result"])
METRIC_ERRORS_TOTAL = Counter("trading_errors_total", "Total system errors", ["type"])
METRIC_CONFIDENCE = Gauge("model_confidence", "Latest model prediction confidence")


class Monitor:
    """
    Real-time monitoring and alerting system.
    Tracks equity curve and sends alerts via Telegram.
    """

    def __init__(self, config: TradingConfig) -> None:
        self.cfg = config
        self.equity_history: List[Dict[str, Any]] = []
        self.bot: Optional[telegram.Bot] = None

        if self.cfg.telegram_token:
            try:
                self.bot = telegram.Bot(token=self.cfg.telegram_token)
                logger.info("Telegram bot initialized")
            except Exception as e:
                logger.error("Failed to initialize Telegram bot: %s", e)

    def start_metrics_server(self) -> None:
        """Start the Prometheus metrics HTTP server."""
        try:
            start_http_server(self.cfg.prometheus_port)
            logger.info("Prometheus metrics server started on port %d", self.cfg.prometheus_port)
        except Exception as e:
            logger.error("Failed to start Prometheus server: %s", e)

    def log_equity(self, equity: float, drawdown: float = 0.0) -> None:
        """Record current equity with timestamp and update metrics."""
        data = {"timestamp": datetime.now(timezone.utc), "equity": equity}
        self.equity_history.append(data)
        METRIC_EQUITY.set(equity)
        METRIC_DRAWDOWN.set(drawdown)
        logger.debug("Equity logged: %.2f (DD: %.2f%%)", equity, drawdown * 100)

    def log_trade(self, side: str, result: str = "closed") -> None:
        """Log a trade execution to Prometheus."""
        METRIC_TRADES_TOTAL.labels(side=side, result=result).inc()
        logger.info("Trade logged: %s (%s)", side, result)

    def log_error(self, error_type: str) -> None:
        """Log a system error to Prometheus."""
        METRIC_ERRORS_TOTAL.labels(type=error_type).inc()
        logger.error("System error logged: %s", error_type)

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
        METRIC_DRAWDOWN.set(drawdown)
        msg = f"🚨 CRITICAL: Circuit Breaker Triggered!\nDrawdown: {drawdown*100:.2f}%\nTrading Halted."
        self.send_message(msg)

    def send_daily_summary(self, pnl: float, trades: int) -> None:
        """Send daily P&L and trade count summary."""
        METRIC_PNL_DAILY.set(pnl)
        status = "PROFIT" if pnl >= 0 else "LOSS"
        msg = (
            f"📅 Daily Summary - {datetime.now(timezone.utc).date()}\n"
            f"Status: {status}\n"
            f"Net P&L: {pnl:.2f}\n"
            f"Trades: {trades}"
        )
        self.send_message(msg)

    def check_confidence_degradation(self, confidence: float) -> None:
        """Send warning if model confidence falls below threshold."""
        METRIC_CONFIDENCE.set(confidence)
        if confidence < self.cfg.confidence_threshold:
            msg = (
                f"⚠️ WARNING: Model Confidence Degradation\n"
                f"Current: {confidence:.3f}\n"
                f"Threshold: {self.cfg.confidence_threshold:.3f}"
            )
            self.send_message(msg)


__all__ = ["Monitor"]

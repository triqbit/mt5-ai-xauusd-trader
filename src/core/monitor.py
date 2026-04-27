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

# Prometheus Metrics
EQUITY_GAUGE = Gauge("trading_equity", "Current account equity")
PNL_GAUGE = Gauge("trading_pnl_daily", "Daily realised PnL")
DRAWDOWN_GAUGE = Gauge("trading_drawdown", "Current peak-to-valley drawdown")
TRADE_COUNTER = Counter("trading_trades_total", "Total trades executed", ["status"])
ERROR_COUNTER = Counter("trading_errors_total", "Total system errors", ["module"])


class Monitor:
    """
    Real-time monitoring and alerting system.
    Tracks equity curve and sends alerts via Telegram.
    """

    def __init__(self, config: TradingConfig) -> None:
        self.cfg = config
        self.equity_history: deque[Dict[str, Any]] = deque(maxlen=1000)
        self.bot: Optional[telegram.Bot] = None
        self._last_alert_time: Dict[str, datetime] = {}
        self._alert_cooldown = 300  # 5 minutes cooldown for same alert type

        if self.cfg.telegram_token:
            try:
                self.bot = telegram.Bot(token=self.cfg.telegram_token)
                logger.info("Telegram bot initialized")
            except Exception as e:
                logger.error("Failed to initialize Telegram bot: %s", e)
                ERROR_COUNTER.labels(module="monitor").inc()

    def start_metrics_server(self) -> None:
        """Start the Prometheus metrics HTTP server."""
        try:
            start_http_server(self.cfg.prometheus_port)
            logger.info("Prometheus metrics server started on port %d", self.cfg.prometheus_port)
        except Exception as e:
            logger.error("Failed to start Prometheus server: %s", e)
            ERROR_COUNTER.labels(module="monitor").inc()

    def log_equity(self, equity: float, drawdown: float = 0.0) -> None:
        """Record current equity and update Prometheus metrics."""
        data = {"timestamp": datetime.now(timezone.utc), "equity": equity}
        self.equity_history.append(data)
        EQUITY_GAUGE.set(equity)
        DRAWDOWN_GAUGE.set(drawdown)
        logger.debug("Equity logged: %.2f | Drawdown: %.2f%%", equity, drawdown * 100)

    def log_trade(self, status: str) -> None:
        """Increment trade counter."""
        TRADE_COUNTER.labels(status=status).inc()

    def log_error(self, module: str) -> None:
        """Increment error counter."""
        ERROR_COUNTER.labels(module=module).inc()

    def send_message(self, text: str, alert_type: Optional[str] = None) -> None:
        """Synchronous wrapper to send Telegram message with throttling."""
        if not self.bot or not self.cfg.telegram_chat_id:
            logger.debug("Telegram bot not configured, message not sent: %s", text)
            return

        # Throttling logic
        if alert_type:
            now = datetime.now(timezone.utc)
            last_time = self._last_alert_time.get(alert_type)
            if last_time and (now - last_time).total_seconds() < self._alert_cooldown:
                logger.debug("Alert '%s' throttled", alert_type)
                return
            self._last_alert_time[alert_type] = now

        try:
            # python-telegram-bot v20+ is async.
            # We use asyncio.run as the main loop is synchronous.
            asyncio.run(self.bot.send_message(chat_id=self.cfg.telegram_chat_id, text=text))
            logger.info("Telegram message sent")
        except Exception as e:
            logger.error("Failed to send Telegram message: %s", e)
            ERROR_COUNTER.labels(module="monitor").inc()

    def alert_circuit_breaker(self, drawdown: float) -> None:
        """Send critical alert for circuit breaker trigger."""
        msg = f"🚨 CRITICAL: Circuit Breaker Triggered!\nDrawdown: {drawdown*100:.2f}%\nTrading Halted."
        self.send_message(msg, alert_type="circuit_breaker")

    def send_daily_summary(self, pnl: float, trades: int) -> None:
        """Send daily P&L and trade count summary and update metrics."""
        status = "PROFIT" if pnl >= 0 else "LOSS"
        msg = (
            f"📅 Daily Summary - {datetime.now(timezone.utc).date()}\n"
            f"Status: {status}\n"
            f"Net P&L: {pnl:.2f}\n"
            f"Trades: {trades}"
        )
        PNL_GAUGE.set(pnl)
        self.send_message(msg)

    def check_confidence_degradation(self, confidence: float) -> None:
        """Send warning if model confidence falls below threshold."""
        if confidence < self.cfg.confidence_threshold:
            msg = (
                f"⚠️ WARNING: Model Confidence Degradation\n"
                f"Current: {confidence:.3f}\n"
                f"Threshold: {self.cfg.confidence_threshold:.3f}"
            )
            self.send_message(msg, alert_type="confidence_degradation")


__all__ = ["Monitor"]

"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/core/monitor.py
Real-time monitoring, equity tracking, Prometheus metrics, and Telegram alerting.
Author : triqbit
License: MIT
"""

from __future__ import annotations

import asyncio
import time
from collections import deque
from collections.abc import Generator
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Any

import psutil
import structlog
import telegram
from prometheus_client import Counter, Gauge, Histogram, start_http_server

from src.core.config import TradingConfig

logger = structlog.get_logger(__name__)

# --- Prometheus Metrics Definitions ---

# 1. Trading Performance Metrics
EQUITY_GAUGE = Gauge("trading_equity", "Current account equity")
DAILY_PNL_GAUGE = Gauge("trading_pnl_daily", "Realized P&L for the current day")
MONTHLY_RETURN_GAUGE = Gauge("trading_return_monthly", "Cumulative return for the current month")
TRADE_COUNTER = Counter("trading_trades_total", "Total number of trades executed")
DRAWDOWN_GAUGE = Gauge("trading_drawdown_percent", "Current account drawdown percentage")
SHARPE_RATIO_GAUGE = Gauge("trading_sharpe_ratio", "Annualized Sharpe Ratio")
WIN_RATE_GAUGE = Gauge("trading_win_rate", "Trading win rate percentage")
AVG_TRADE_DURATION_GAUGE = Gauge(
    "trading_avg_trade_duration_seconds", "Mean trade holding time in seconds"
)

# 2. Execution Metrics
EXECUTION_LATENCY_HISTOGRAM = Histogram(
    "trading_execution_latency_seconds", "Time from signal to execution"
)
SLIPPAGE_HISTOGRAM = Histogram(
    "trading_slippage_pips", "Difference between expected and actual price"
)
FILL_RATE_GAUGE = Gauge("trading_fill_rate", "Percentage of orders filled at intended price")
REJECTED_ORDER_COUNTER = Counter(
    "trading_orders_rejected_total", "Total number of rejected orders", ["reason"]
)
INTERNAL_REJECTION_COUNTER = Counter(
    "trading_internal_rejections_total",
    "Total number of internal signal rejections",
    ["component", "reason"],
)
PARTIAL_FILL_COUNTER = Counter("trading_partial_fills_total", "Total number of partial fills")

# 3. System Health Metrics
CPU_USAGE_GAUGE = Gauge("system_cpu_usage_percent", "System CPU utilization percentage")
MEMORY_USAGE_GAUGE = Gauge("system_memory_usage_percent", "System memory usage percentage")
DISK_USAGE_GAUGE = Gauge("system_disk_usage_percent", "System disk usage percentage")
CIRCUIT_BREAKER_STATE_GAUGE = Gauge(
    "trading_circuit_breaker_state",
    "Current state of the circuit breaker (0=CLOSED, 1=HALF_OPEN, 2=OPEN)",
    ["name"],
)
SYSTEM_ERROR_COUNTER = Counter(
    "trading_system_errors", "Total count of system errors", ["component"]
)
TRADING_BLOCK_DURATION = Histogram(
    "trading_block_duration_seconds",
    "Duration of trading code blocks in seconds",
    ["block_label"],
)

# 4. Model Metrics
CONFIDENCE_GAUGE = Gauge("trading_model_confidence", "Latest model prediction confidence")
MODEL_ACCURACY_GAUGE = Gauge("trading_model_accuracy", "Model prediction accuracy")
MODEL_DRIFT_GAUGE = Gauge("trading_model_drift_score", "Statistical drift from baseline")
MODEL_CALIBRATION_GAUGE = Gauge(
    "trading_model_calibration_error", "Expected Calibration Error (ECE)"
)

# 5. Data Quality Metrics
DATA_FRESHNESS_GAUGE = Gauge(
    "trading_data_freshness_seconds", "Age of latest data point in seconds"
)

# 6. Portfolio & Market Regime Metrics
MARKET_REGIME_GAUGE = Gauge(
    "trading_market_regime", "Numeric mapping of current market regime"
)
REGIME_CONFIDENCE_GAUGE = Gauge(
    "trading_regime_confidence", "Model confidence in the detected regime"
)
PORTFOLIO_HEAT_TOTAL_GAUGE = Gauge(
    "trading_portfolio_heat_total", "Total portfolio risk commitment (0.0 to 1.0)"
)
PORTFOLIO_HEAT_SYMBOL_GAUGE = Gauge(
    "trading_portfolio_heat_symbol", "Risk commitment per symbol (0.0 to 1.0)", ["symbol"]
)


class Monitor:
    """
    Real-time monitoring and alerting system.
    Tracks equity curve, updates Prometheus metrics, and sends alerts via Telegram.
    """

    def __init__(self, config: TradingConfig) -> None:
        """
        Initialize the Monitor with configuration.

        Args:
            config: The trading configuration object.
        """
        self.cfg = config
        self.equity_history: deque[dict[str, Any]] = deque(maxlen=1000)
        self.bot: telegram.Bot | None = None
        self._server_started = False
        self._background_tasks: set[asyncio.Task] = set()

        # Initialize psutil for non-blocking cpu_percent calls
        psutil.cpu_percent(interval=None)

        telegram_token = self.cfg.telegram_token.get_secret_value()
        if telegram_token:
            try:
                self.bot = telegram.Bot(token=telegram_token)
                logger.info("telegram_bot_initialized")
            except Exception as e:
                logger.error("telegram_bot_init_failed", error=str(e))

    def start_metrics_server(self) -> None:
        """Start the Prometheus metrics server if not already running."""
        if self._server_started:
            return
        try:
            start_http_server(self.cfg.prometheus_port)
            self._server_started = True
            logger.info("prometheus_server_started", port=self.cfg.prometheus_port)

            # Start background task for system metrics
            try:
                loop = asyncio.get_running_loop()
                task = loop.create_task(self._collect_system_metrics())
                self._background_tasks.add(task)
                task.add_done_callback(self._background_tasks.discard)
            except RuntimeError:
                # If no loop is running (e.g. during startup), we don't start the background task here.
                # In a real app, main.py ensures a loop is running.
                logger.warning("no_running_loop_skipping_system_metrics")
        except Exception as e:
            logger.error("failed_to_start_prometheus_server", error=str(e))

    async def _collect_system_metrics(self, interval: int = 60) -> None:
        """Background task to collect system metrics periodically."""
        logger.info("system_metrics_collection_started", interval_seconds=interval)
        while True:
            try:
                cpu = psutil.cpu_percent(interval=None)
                memory = psutil.virtual_memory().percent
                disk = psutil.disk_usage("/").percent

                CPU_USAGE_GAUGE.set(cpu)
                MEMORY_USAGE_GAUGE.set(memory)
                DISK_USAGE_GAUGE.set(disk)

                logger.debug("system_metrics_updated", cpu=cpu, memory=memory, disk=disk)
            except Exception as e:
                logger.error("failed_to_collect_system_metrics", error=str(e))

            await asyncio.sleep(interval)

    def log_equity(self, equity: float) -> None:
        """Record current equity and update Prometheus metrics."""
        data = {"timestamp": datetime.now(UTC), "equity": equity}
        self.equity_history.append(data)
        EQUITY_GAUGE.set(equity)
        logger.debug("equity_logged", equity=equity)

    def log_pnl(self, pnl: float) -> None:
        """Update daily P&L metric."""
        DAILY_PNL_GAUGE.set(pnl)
        logger.debug("pnl_logged", pnl=pnl)

    def log_monthly_return(self, monthly_return: float) -> None:
        """Update monthly return metric."""
        MONTHLY_RETURN_GAUGE.set(monthly_return)
        logger.debug("monthly_return_logged", monthly_return=monthly_return)

    def log_trade_duration(self, avg_duration_seconds: float) -> None:
        """Update average trade duration metric."""
        AVG_TRADE_DURATION_GAUGE.set(avg_duration_seconds)
        logger.debug("trade_duration_logged", avg_duration=avg_duration_seconds)

    def send_message(self, text: str) -> None:
        """
        Synchronous wrapper to send Telegram message.
        Handles both synchronous and asynchronous contexts safely.
        """
        if not self.bot or not self.cfg.telegram_chat_id:
            logger.debug("telegram_not_configured", message=text)
            return

        async def _send():
            try:
                await self.bot.send_message(chat_id=self.cfg.telegram_chat_id, text=text)
                logger.info("telegram_message_sent")
            except Exception as e:
                logger.error("telegram_send_failed", error=str(e))

        try:
            try:
                loop = asyncio.get_running_loop()
                # We are inside a running event loop, schedule task
                task = loop.create_task(_send())
                self._background_tasks.add(task)
                task.add_done_callback(self._background_tasks.discard)
            except RuntimeError:
                # No event loop is running, use asyncio.run (blocking)
                asyncio.run(_send())
        except Exception as e:
            logger.error("send_message_wrapper_failed", error=str(e))

    def alert_circuit_breaker(self, drawdown: float) -> None:
        """Send critical alert for circuit breaker trigger and update metrics."""
        DRAWDOWN_GAUGE.set(drawdown * 100)
        msg = f"🚨 CRITICAL: Circuit Breaker Triggered!\nDrawdown: {drawdown * 100:.2f}%\nTrading Halted."
        self.send_message(msg)
        logger.critical("circuit_breaker_triggered", drawdown_pct=drawdown * 100)

    def send_daily_summary(self, pnl: float, trades: int) -> None:
        """Send daily P&L and trade count summary and update metrics."""
        DAILY_PNL_GAUGE.set(pnl)
        status = "PROFIT" if pnl >= 0 else "LOSS"
        msg = (
            f"📅 Daily Summary - {datetime.now(UTC).date()}\n"
            f"Status: {status}\n"
            f"Net P&L: {pnl:.2f}\n"
            f"Trades Today: {trades}"
        )
        self.send_message(msg)
        logger.info("daily_summary_sent", pnl=pnl, trades=trades)

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
            logger.warning(
                "model_confidence_degradation",
                confidence=confidence,
                threshold=self.cfg.confidence_threshold,
            )

    def record_trade(self) -> None:
        """Increment the total trade counter."""
        TRADE_COUNTER.inc()

    def update_circuit_breaker_state(self, name: str, state: str) -> None:
        """
        Update the circuit breaker state metric.
        0 = CLOSED, 1 = HALF_OPEN, 2 = OPEN
        """
        state_map = {"CLOSED": 0, "HALF_OPEN": 1, "OPEN": 2}
        val = state_map.get(state, 2)  # Default to OPEN if unknown
        CIRCUIT_BREAKER_STATE_GAUGE.labels(name=name).set(val)
        logger.info("circuit_breaker_state_updated", name=name, state=state, value=val)

    def log_system_error(self, component: str, error_message: str) -> None:
        """Log system errors to Prometheus and send a Telegram alert."""
        SYSTEM_ERROR_COUNTER.labels(component=component).inc()
        msg = f"❌ SYSTEM ERROR: {component}\nError: {error_message}"
        self.send_message(msg)
        logger.error("system_error_logged", component=component, error=error_message)

    def update_performance_metrics(self, win_rate: float, sharpe_ratio: float) -> None:
        """Update Sharpe Ratio and Win Rate Prometheus metrics."""
        WIN_RATE_GAUGE.set(win_rate * 100)
        SHARPE_RATIO_GAUGE.set(sharpe_ratio)
        logger.debug(
            "performance_metrics_updated",
            win_rate_pct=win_rate * 100,
            sharpe_ratio=sharpe_ratio,
        )

    def alert_balance_mismatch(self, broker_balance: float, local_balance: float) -> None:
        """Send critical alert for account balance mismatch."""
        diff = abs(broker_balance - local_balance)
        diff_pct = (diff / broker_balance) * 100 if broker_balance > 0 else 0
        msg = (
            f"🚨 CRITICAL: Balance Mismatch Detected!\n"
            f"Broker: {broker_balance:.2f}\n"
            f"Local: {local_balance:.2f}\n"
            f"Difference: {diff_pct:.2f}%"
        )
        self.send_message(msg)
        logger.error(
            "balance_mismatch_detected",
            broker=broker_balance,
            local=local_balance,
            diff_pct=diff_pct,
        )

    def alert_margin_call(self, margin_ratio: float) -> None:
        """Send critical alert for low margin ratio."""
        msg = f"🚨 CRITICAL: Margin Call Warning!\nMargin Ratio: {margin_ratio:.2f}%"
        self.send_message(msg)
        logger.error("margin_call_warning", margin_ratio=margin_ratio)

    def alert_liquidity_crisis(self, symbol: str, spread: float) -> None:
        """Send critical alert for liquidity crisis (extreme spread)."""
        msg = f"🚨 CRITICAL: Liquidity Crisis!\nSymbol: {symbol}\nSpread: {spread:.2f} pips"
        self.send_message(msg)
        logger.warning("liquidity_crisis_alert", symbol=symbol, spread=spread)

    def alert_broker_connection_lost(self) -> None:
        """Send critical alert for broker connection loss."""
        msg = "🚨 CRITICAL: Broker Connection Lost!\nAttempting reconnection..."
        self.send_message(msg)
        logger.error("broker_connection_lost_alert")

    def alert_broker_connection_restored(self) -> None:
        """Send notification for broker connection restoration."""
        msg = "✅ INFO: Broker Connection Restored."
        self.send_message(msg)
        logger.info("broker_connection_restored_alert")

    def log_execution_quality(
        self, latency_ms: float, slippage_pips: float, fill_rate: float
    ) -> None:
        """Log execution quality metrics to Prometheus."""
        latency_seconds = latency_ms / 1000.0
        EXECUTION_LATENCY_HISTOGRAM.observe(latency_seconds)
        SLIPPAGE_HISTOGRAM.observe(slippage_pips)
        FILL_RATE_GAUGE.set(fill_rate * 100)
        logger.debug(
            "execution_quality_logged",
            latency_ms=latency_ms,
            slippage=slippage_pips,
            fill_rate=fill_rate,
        )

        threshold = (
            self.cfg.execution_latency_threshold
            if hasattr(self.cfg, "execution_latency_threshold")
            else 0.5
        )
        if latency_seconds > threshold:
            msg = (
                f"🚨 CRITICAL: High Execution Latency!\n"
                f"Latency: {latency_ms:.2f}ms\n"
                f"Threshold: {threshold * 1000:.2f}ms"
            )
            self.send_message(msg)
            logger.error("high_execution_latency_alert", latency_ms=latency_ms)

    def record_rejection(self, reason: str) -> None:
        """Record a rejected order."""
        REJECTED_ORDER_COUNTER.labels(reason=reason).inc()
        logger.warning("order_rejected", reason=reason)

    def record_internal_rejection(self, component: str, reason: str) -> None:
        """Record an internal signal rejection from a specific component."""
        INTERNAL_REJECTION_COUNTER.labels(component=component, reason=reason).inc()
        logger.info("internal_rejection_recorded", component=component, reason=reason)

    def record_partial_fill(self) -> None:
        """Record a partial fill."""
        PARTIAL_FILL_COUNTER.inc()
        logger.info("partial_fill_recorded")

    def log_model_performance(
        self, accuracy: float, drift_score: float, calibration_error: float = 0.0
    ) -> None:
        """Log model performance metrics and send alerts if thresholds are breached."""
        MODEL_ACCURACY_GAUGE.set(accuracy * 100)
        MODEL_DRIFT_GAUGE.set(drift_score)
        MODEL_CALIBRATION_GAUGE.set(calibration_error)
        logger.info(
            "model_performance_logged",
            accuracy=accuracy,
            drift=drift_score,
            calibration=calibration_error,
        )

        if accuracy < self.cfg.model_accuracy_floor:
            msg = (
                f"⚠️ WARNING: Model Accuracy Below Floor\n"
                f"Current: {accuracy:.2%}\n"
                f"Floor: {self.cfg.model_accuracy_floor:.2%}"
            )
            self.send_message(msg)
            logger.warning(
                "model_accuracy_alert", accuracy=accuracy, floor=self.cfg.model_accuracy_floor
            )

        if drift_score > self.cfg.model_drift_threshold:
            msg = (
                f"⚠️ WARNING: Model Drift Detected\n"
                f"Current Score: {drift_score:.3f}\n"
                f"Threshold: {self.cfg.model_drift_threshold:.3f}"
            )
            self.send_message(msg)
            logger.warning(
                "model_drift_alert", drift=drift_score, threshold=self.cfg.model_drift_threshold
            )

        if calibration_error > self.cfg.model_calibration_threshold:
            msg = (
                f"⚠️ WARNING: Model Calibration Error Detected\n"
                f"Current Error: {calibration_error:.3f}\n"
                f"Threshold: {self.cfg.model_calibration_threshold:.3f}"
            )
            self.send_message(msg)
            logger.warning(
                "model_calibration_alert",
                calibration=calibration_error,
                threshold=self.cfg.model_calibration_threshold,
            )

    def log_data_freshness(self, timestamp: datetime) -> None:
        """
        Log data freshness metric and alert if data is stale.

        Args:
            timestamp: The timestamp of the latest data point.
        """
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=UTC)
        age = (datetime.now(UTC) - timestamp).total_seconds()
        DATA_FRESHNESS_GAUGE.set(age)
        logger.debug("data_freshness_logged", age_seconds=age)

        if age > self.cfg.data_freshness_threshold:
            msg = f"⚠️ WARNING: Data Stale!\nLast Data Point: {age / 60:.1f} minutes ago."
            self.send_message(msg)
            logger.warning("stale_data_alert", age_seconds=age)

    def update_market_regime(self, regime_label: str, confidence: float) -> None:
        """Update market regime metrics."""
        # Mapping: ranging=0, trending=1, volatile_breakout=2, low_volatility_drift=3, news_shock=4, mean_reversion=5
        mapping = {
            "ranging": 0,
            "trending": 1,
            "volatile_breakout": 2,
            "low_volatility_drift": 3,
            "news_shock": 4,
            "mean_reversion": 5,
        }
        val = mapping.get(regime_label.lower(), -1)
        MARKET_REGIME_GAUGE.set(val)
        REGIME_CONFIDENCE_GAUGE.set(confidence)
        logger.debug("market_regime_metrics_updated", label=regime_label, val=val, conf=confidence)

    def update_portfolio_heat(self, total_heat: float, symbol_heats: dict[str, float]) -> None:
        """Update portfolio heat metrics."""
        PORTFOLIO_HEAT_TOTAL_GAUGE.set(total_heat)
        for symbol, heat in symbol_heats.items():
            PORTFOLIO_HEAT_SYMBOL_GAUGE.labels(symbol=symbol).set(heat)
        logger.debug("portfolio_heat_metrics_updated", total=total_heat)

    def log_drawdown(self, drawdown_pct: float) -> None:
        """Update drawdown metric."""
        DRAWDOWN_GAUGE.set(drawdown_pct)
        logger.debug("drawdown_logged", drawdown_pct=drawdown_pct)

    def alert_inference_timeout(self, latency_ms: float, threshold_ms: float) -> None:
        """Send warning for model inference timeout."""
        msg = f"⚠️ WARNING: Model Inference Timeout!\nLatency: {latency_ms:.2f}ms\nThreshold: {threshold_ms:.2f}ms"
        self.send_message(msg)
        logger.warning("model_inference_timeout_alert", latency_ms=latency_ms)

    def alert_feature_missing(self, feature_name: str) -> None:
        """Send warning for missing model feature."""
        msg = f"⚠️ WARNING: Missing Model Feature: {feature_name}"
        self.send_message(msg)
        logger.warning("missing_feature_alert", feature=feature_name)

    def alert_stale_model(self, age_days: float) -> None:
        """Send warning for stale model weights."""
        msg = f"⚠️ WARNING: Stale Model Detected!\nAge: {age_days:.1f} days."
        self.send_message(msg)
        logger.warning("stale_model_alert", age_days=age_days)

    def alert_training_failed(self, error: str) -> None:
        """Send critical alert for model retraining failure."""
        msg = f"❌ CRITICAL: Model Retraining Failed!\nError: {error}"
        self.send_message(msg)
        logger.error("model_training_failed_alert", error=error)

    @contextmanager
    def track_block_duration(self, label: str) -> Generator[None, None, None]:
        """Context manager to track the duration of a code block."""
        start_time = time.perf_counter()
        try:
            yield
        finally:
            duration = time.perf_counter() - start_time
            TRADING_BLOCK_DURATION.labels(block_label=label).observe(duration)
            logger.debug("block_duration_tracked", label=label, duration=duration)

    def get_equity_curve(self) -> list[dict[str, Any]]:
        """Return the tracked equity curve history."""
        return list(self.equity_history)


__all__ = ["Monitor"]

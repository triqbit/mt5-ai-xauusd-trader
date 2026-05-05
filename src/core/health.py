"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/core/health.py
Enterprise-grade health check system for production monitoring.
Author : triqbit
License: MIT
"""

from __future__ import annotations

import logging
import shutil
from datetime import UTC, datetime
from enum import Enum

import redis
from fastapi import APIRouter, FastAPI, HTTPException, status
from fastapi.encoders import jsonable_encoder
from prometheus_client import Gauge, make_asgi_app
from pydantic import BaseModel, Field

from src.core.audit_log import AuditLogger
from src.core.config import TradingConfig, get_config
from src.core.config_validator import ConfigValidator
from src.core.trade_logger import TradeLogger
from src.trading.mt5_connector import MT5Connector

logger = logging.getLogger(__name__)

# --- Prometheus Metrics for Component Health ---
HEALTH_GAUGES = Gauge(
    "system_component_health",
    "Status of system components (1.0=Healthy, 0.5=Degraded, 0.0=Failed)",
    ["component"],
)


class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILED = "failed"


class ComponentStatus(BaseModel):
    status: HealthStatus
    message: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class HealthReport(BaseModel):
    status: HealthStatus
    components: dict[str, ComponentStatus]
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class HealthChecker:
    """
    Enterprise health checker for production monitoring and startup gating.
    """

    def __init__(
        self,
        config: TradingConfig,
        connector: MT5Connector | None = None,
        trade_logger: TradeLogger | None = None,
        model: object | None = None,
        audit_logger: AuditLogger | None = None,
    ) -> None:
        self.cfg = config
        self.connector = connector
        self.trade_logger = trade_logger
        self.model = model
        self.audit_logger = audit_logger

    def _update_gauge(self, component: str, status: HealthStatus) -> None:
        """Helper to update Prometheus health gauge."""
        val = (
            1.0
            if status == HealthStatus.HEALTHY
            else (0.5 if status == HealthStatus.DEGRADED else 0.0)
        )
        HEALTH_GAUGES.labels(component=component).set(val)

    def check_liveness(self) -> ComponentStatus:
        """Basic application responsiveness check."""
        res = ComponentStatus(status=HealthStatus.HEALTHY, message="Application is running")
        self._update_gauge("liveness", res.status)
        return res

    def check_database(self) -> ComponentStatus:
        """Verify database reachability."""
        if not self.trade_logger:
            res = ComponentStatus(status=HealthStatus.FAILED, message="TradeLogger not initialized")
            self._update_gauge("database", res.status)
            return res

        try:
            # Simple connectivity check using SQLAlchemy engine
            with self.trade_logger.engine.connect() as conn:
                conn.execute(self.trade_logger.engine.dialect.do_ping(conn.connection))
            res = ComponentStatus(status=HealthStatus.HEALTHY, message="Database reachable")
        except Exception as e:
            logger.error("Health check - Database failure: %s", e)
            res = ComponentStatus(
                status=HealthStatus.FAILED, message=f"Database unreachable: {e!s}"
            )

        self._update_gauge("database", res.status)
        return res

    def check_mt5(self) -> ComponentStatus:
        """Verify MT5 connection status with an active responsiveness check."""
        if not self.connector:
            res = ComponentStatus(
                status=HealthStatus.FAILED, message="MT5Connector not initialized"
            )
            self._update_gauge("mt5", res.status)
            return res

        if not self.connector._is_initialized:
            res = ComponentStatus(
                status=HealthStatus.FAILED, message="MT5 connection not initialized"
            )
            self._update_gauge("mt5", res.status)
            return res

        try:
            # Active check by attempting to fetch account info (lightweight call)
            # For MetaAPI fallback, get_account_info currently returns {} as it's not implemented,
            # so we only perform the active check for native MT5.
            if getattr(self.connector, "use_metaapi", False):
                res = ComponentStatus(
                    status=HealthStatus.HEALTHY, message="MT5 connection alive (MetaAPI fallback)"
                )
            else:
                info = self.connector.get_account_info()
                if info:
                    res = ComponentStatus(
                        status=HealthStatus.HEALTHY, message="MT5 connection active and responding"
                    )
                else:
                    res = ComponentStatus(
                        status=HealthStatus.FAILED,
                        message="MT5 connection failed to return account info",
                    )
        except Exception as e:
            logger.error("Health check - MT5 failure: %s", e)
            res = ComponentStatus(status=HealthStatus.FAILED, message=f"MT5 API call failed: {e!s}")

        self._update_gauge("mt5", res.status)
        return res

    def check_models(self) -> ComponentStatus:
        """Verify models are loaded in the ensemble or individual wrappers."""
        if not self.model:
            res = ComponentStatus(
                status=HealthStatus.FAILED, message="Model orchestrator not initialized"
            )
            self._update_gauge("models", res.status)
            return res

        # Use hasattr/getattr to avoid strict type dependency on torch-heavy models
        loaded = []

        # 1. Check for EnsembleModel composition
        if getattr(self.model, "_ppo_model", None) is not None:
            loaded.append("PPO (Ensemble)")
        if getattr(self.model, "lstm_model", None) is not None:
            loaded.append("LSTM (Ensemble)")
        if getattr(self.model, "_dreamer_model", None) is not None:
            loaded.append("Dreamer (Ensemble)")

        # 2. Check for individual model wrappers (PPOAgent, LSTMModel)
        if (
            not loaded
            and hasattr(self.model, "model")
            and getattr(self.model, "model", None) is not None
        ):
            class_name = self.model.__class__.__name__
            loaded.append(f"{class_name} (Loaded)")

        if not loaded:
            res = ComponentStatus(status=HealthStatus.FAILED, message="No models loaded in system")
        else:
            # Check for model health/drift if available
            health_msg = f"Models loaded: {', '.join(loaded)}"
            if hasattr(self.model, "get_health_metrics"):
                try:
                    metrics = self.model.get_health_metrics()
                    if metrics:
                        drift = float(metrics.get("drift", 0.0))
                        acc = float(metrics.get("accuracy", 1.0))
                        health_msg += f" | Agg Health: acc={acc:.2f} drift={drift:.2f}"
                except (TypeError, ValueError):
                    # Handle cases where metrics might be MagicMocks in tests
                    pass

            res = ComponentStatus(status=HealthStatus.HEALTHY, message=health_msg)

        self._update_gauge("models", res.status)
        return res

    def check_config(self) -> ComponentStatus:
        """Validate current environment configuration."""
        validator = ConfigValidator(self.cfg)
        result = validator.validate()

        if result.success:
            if result.errors:
                res = ComponentStatus(
                    status=HealthStatus.DEGRADED,
                    message=f"Config valid with warnings: {'; '.join(e.message for e in result.errors)}",
                )
            else:
                res = ComponentStatus(status=HealthStatus.HEALTHY, message="Configuration valid")
        else:
            critical_errors = [e.message for e in result.errors if e.critical]
            res = ComponentStatus(
                status=HealthStatus.FAILED,
                message=f"Configuration invalid: {'; '.join(critical_errors)}",
            )

        self._update_gauge("config", res.status)
        return res

    def check_disk_space(self, min_mb: int = 100) -> ComponentStatus:
        """Check for sufficient disk space in log directory."""
        logs_dir = self.cfg.logs_dir
        if not logs_dir.exists():
            try:
                logs_dir.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                res = ComponentStatus(
                    status=HealthStatus.FAILED, message=f"Cannot create logs directory: {e}"
                )
                self._update_gauge("disk", res.status)
                return res

        usage = shutil.disk_usage(logs_dir)
        free_mb = usage.free / (1024 * 1024)

        if free_mb < min_mb:
            res = ComponentStatus(
                status=HealthStatus.FAILED,
                message=f"Low disk space: {free_mb:.2f}MB free, required {min_mb}MB",
            )
        else:
            res = ComponentStatus(
                status=HealthStatus.HEALTHY, message=f"Disk space sufficient: {free_mb:.2f}MB free"
            )

        self._update_gauge("disk", res.status)
        return res

    def check_redis(self) -> ComponentStatus:
        """
        Verify Redis connectivity.
        Non-blocking: returns DEGRADED instead of FAILED if not configured or unreachable.
        """
        if not self.cfg.redis_url:
            res = ComponentStatus(
                status=HealthStatus.DEGRADED, message="Redis URL not configured (Optional)"
            )
            self._update_gauge("redis", res.status)
            return res

        try:
            client = redis.from_url(self.cfg.redis_url, socket_timeout=2)
            if client.ping():
                res = ComponentStatus(status=HealthStatus.HEALTHY, message="Redis reachable")
            else:
                res = ComponentStatus(status=HealthStatus.DEGRADED, message="Redis ping failed")
        except Exception as e:
            logger.warning("Health check - Redis degradation: %s", e)
            res = ComponentStatus(status=HealthStatus.DEGRADED, message=f"Redis unreachable: {e!s}")

        self._update_gauge("redis", res.status)
        return res

    def check_audit_log(self) -> ComponentStatus:
        """Verify AuditLogger initialization status."""
        if not self.audit_logger:
            res = ComponentStatus(status=HealthStatus.FAILED, message="AuditLogger not initialized")
            self._update_gauge("audit_log", res.status)
            return res

        if self.audit_logger._initialized:
            res = ComponentStatus(
                status=HealthStatus.HEALTHY, message="AuditLogger initialized and active"
            )
        else:
            res = ComponentStatus(
                status=HealthStatus.FAILED, message="AuditLogger not properly initialized"
            )

        self._update_gauge("audit_log", res.status)
        return res

    def get_full_report(self) -> HealthReport:
        """Aggregate all checks into a comprehensive report."""
        components = {
            "liveness": self.check_liveness(),
            "database": self.check_database(),
            "mt5": self.check_mt5(),
            "models": self.check_models(),
            "config": self.check_config(),
            "disk": self.check_disk_space(),
            "redis": self.check_redis(),
            "audit_log": self.check_audit_log(),
        }

        # Determine overall status
        failed = any(c.status == HealthStatus.FAILED for c in components.values())
        degraded = any(c.status == HealthStatus.DEGRADED for c in components.values())

        overall_status = (
            HealthStatus.FAILED
            if failed
            else (HealthStatus.DEGRADED if degraded else HealthStatus.HEALTHY)
        )

        return HealthReport(status=overall_status, components=components)

    def startup_gate(self) -> HealthReport:
        """
        Enforce a health check gate at startup.
        Raises RuntimeError if critical health checks fail.

        Returns:
            The final HealthReport generated during the gate.
        """
        report = self.get_full_report()
        if report.status == HealthStatus.FAILED:
            failed_components = [
                name
                for name, comp in report.components.items()
                if comp.status == HealthStatus.FAILED
            ]
            msg = f"Startup health gate FAILED. Critical components: {', '.join(failed_components)}"
            logger.critical(msg)
            if self.audit_logger:
                self.audit_logger.log("system", "startup_gate_failure", msg)
            raise RuntimeError(msg)

        if report.status == HealthStatus.DEGRADED:
            warnings = [
                name
                for name, comp in report.components.items()
                if comp.status == HealthStatus.DEGRADED
            ]
            msg = f"Startup health gate PASSED with warnings in: {', '.join(warnings)}"
            logger.warning(msg)
            if self.audit_logger:
                self.audit_logger.log("system", "startup_gate_warning", msg)
        else:
            logger.info("Startup health gate PASSED successfully")
            if self.audit_logger:
                self.audit_logger.log("system", "startup_gate_success", "All health checks passed")

        return report


# FastAPI Router implementation
router = APIRouter(prefix="/health", tags=["health"])

# Global health checker instance - to be configured at startup
_health_checker: HealthChecker | None = None


def get_health_checker() -> HealthChecker:
    global _health_checker
    if _health_checker is None:
        # Fallback for when not properly initialized
        _health_checker = HealthChecker(get_config())
    return _health_checker


def init_health_checker(
    config: TradingConfig,
    connector: MT5Connector,
    trade_logger: TradeLogger,
    model: object,
    audit_logger: AuditLogger | None = None,
) -> HealthChecker:
    global _health_checker
    _health_checker = HealthChecker(config, connector, trade_logger, model, audit_logger)
    return _health_checker


def create_health_app() -> FastAPI:
    """
    Create a FastAPI application that includes health routes and Prometheus metrics.
    """
    app = FastAPI(
        title="MT5 Trading Bot Health API",
        description="Enterprise health monitoring and metrics for MT5 AI/ML Bot",
        version="1.0.0",
    )
    app.include_router(router)

    # Mount Prometheus metrics app
    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)

    return app


@router.get("/liveness", response_model=ComponentStatus)
async def liveness():
    checker = get_health_checker()
    return checker.check_liveness()


@router.get("/readiness", response_model=HealthReport)
async def readiness():
    checker = get_health_checker()
    report = checker.get_full_report()

    if report.status == HealthStatus.FAILED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=jsonable_encoder(report),
        )
    return report


@router.get("/full", response_model=HealthReport)
async def full_report():
    checker = get_health_checker()
    return checker.get_full_report()

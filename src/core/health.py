"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/core/health.py
Enterprise-grade health check system for production monitoring.
Implements Liveness/Readiness probes and deep dependency monitoring.
Author : triqbit
License: MIT
"""

from __future__ import annotations

import contextlib
import logging
import platform
import shutil
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional

import psutil
import redis
from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.encoders import jsonable_encoder
from prometheus_client import Gauge, make_asgi_app
from pydantic import BaseModel, Field
from sqlalchemy import text

from src.core.audit_log import AuditLogger
from src.core.config import TradingConfig, get_config
from src.core.config_validator import ConfigValidator
from src.core.trade_logger import TradeLogger
from src.trading.mt5_connector import MT5Connector

logger = logging.getLogger(__name__)

# --- Prometheus Metrics for Component Health ---
# 1.0 = Healthy, 0.5 = Degraded, 0.0 = Failed
HEALTH_GAUGES = Gauge(
    "system_component_health",
    "Status of system components (1.0=Healthy, 0.5=Degraded, 0.0=Failed)",
    ["component"],
)


class HealthStatus(str, Enum):
    """Enumeration of possible health states for the system and its components."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILED = "failed"


def get_system_version() -> str:
    """Utility to retrieve application version from the source package."""
    try:
        from src import __version__

        return __version__
    except ImportError:
        return "unknown"


class ComponentStatus(BaseModel):
    """
    Status of an individual system component.
    Includes status, descriptive message, suggested remedy, and UTC timestamp.
    """

    status: HealthStatus
    message: str
    remedy: str = "N/A"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class HealthReport(BaseModel):
    """
    Aggregate health report containing status of all tracked components.
    Used for readiness probes and detailed diagnostics.
    """

    status: HealthStatus
    version: str = "unknown"
    environment: str = "production"
    components: Dict[str, ComponentStatus]
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class HealthChecker:
    """
    Enterprise health checker for production monitoring and startup gating.
    Implements probes and dependency checks aligned with SLO targets and
    Enterprise Release Standards.
    """

    def __init__(
        self,
        config: TradingConfig,
        connector: Optional[MT5Connector] = None,
        trade_logger: Optional[TradeLogger] = None,
        model: Optional[Any] = None,
        audit_logger: Optional[AuditLogger] = None,
    ) -> None:
        """
        Initialize the HealthChecker with system dependencies.

        Args:
            config: System configuration.
            connector: MT5/MetaAPI connector instance.
            trade_logger: Database logger for trades.
            model: Model orchestrator or individual model instance.
            audit_logger: Enterprise audit logger.
        """
        self.cfg = config
        self.connector = connector
        self.trade_logger = trade_logger
        self.model = model
        self.audit_logger = audit_logger
        # Initialize psutil for non-blocking CPU checks (first call returns 0.0)
        psutil.cpu_percent(interval=None)

    def _update_gauge(self, component: str, status: HealthStatus) -> None:
        """Update Prometheus health gauge for a specific component."""
        val = (
            1.0
            if status == HealthStatus.HEALTHY
            else (0.5 if status == HealthStatus.DEGRADED else 0.0)
        )
        HEALTH_GAUGES.labels(component=component).set(val)

    def check_liveness(self) -> ComponentStatus:
        """
        Liveness probe: is the process running and responsive?
        Lightweight check to indicate the application is not deadlocked.
        """
        res = ComponentStatus(status=HealthStatus.HEALTHY, message="Application heartbeat active")
        self._update_gauge("liveness", res.status)
        return res

    def check_environment(self) -> ComponentStatus:
        """Report on the execution environment (OS, Python, Hardware)."""
        py_ver = platform.python_version()
        os_info = f"{platform.system()} {platform.release()}"
        arch = platform.machine()

        hardware = "CPU"
        try:
            import torch

            if torch.cuda.is_available():
                hardware = f"GPU (CUDA: {torch.cuda.get_device_name(0)})"
            elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                hardware = "GPU (MPS)"
        except ImportError:
            hardware = "CPU (PyTorch not installed)"

        msg = f"Python {py_ver} on {os_info} ({arch}) | Hardware: {hardware}"
        res = ComponentStatus(status=HealthStatus.HEALTHY, message=msg)
        self._update_gauge("environment", res.status)
        return res

    def check_system_resources(
        self, cpu_threshold: float = 90.0, mem_threshold: float = 90.0
    ) -> ComponentStatus:
        """
        Monitor CPU and Memory usage.
        Non-blocking check (interval=None) assumes previous initialization in __init__.
        """
        cpu_usage = psutil.cpu_percent(interval=None)
        mem = psutil.virtual_memory()
        mem_usage = mem.percent

        status = HealthStatus.HEALTHY
        messages = [f"CPU: {cpu_usage}%", f"MEM: {mem_usage}%"]
        remedies = []

        if cpu_usage > cpu_threshold:
            status = HealthStatus.DEGRADED
            remedies.append("Check for runaway processes or increase CPU allocation")
        if mem_usage > mem_threshold:
            status = HealthStatus.DEGRADED
            remedies.append("Check for memory leaks or increase RAM allocation")

        res = ComponentStatus(
            status=status,
            message=" | ".join(messages),
            remedy="; ".join(remedies) if remedies else "N/A",
        )
        self._update_gauge("system_resources", res.status)
        return res

    def check_database(self) -> ComponentStatus:
        """Verify primary database reachability via connectivity test."""
        if not self.trade_logger:
            res = ComponentStatus(
                status=HealthStatus.FAILED,
                message="TradeLogger not initialized",
                remedy="Ensure DATABASE_URL is valid in .env and Database service is running",
            )
            self._update_gauge("database", res.status)
            return res

        try:
            with self.trade_logger.engine.connect() as conn:
                # Use dialect-specific ping if available, fallback to simple SELECT
                try:
                    conn.execute(self.trade_logger.engine.dialect.do_ping(conn.connection))
                except (AttributeError, Exception):
                    conn.execute(text("SELECT 1"))
            res = ComponentStatus(status=HealthStatus.HEALTHY, message="Database reachable")
        except Exception as e:
            logger.error("Health check - Database failure: %s", e)
            res = ComponentStatus(
                status=HealthStatus.FAILED,
                message=f"Database unreachable: {e!s}",
                remedy="Verify database service is running and connection string (DATABASE_URL) is correct",
            )

        self._update_gauge("database", res.status)
        return res

    def check_mt5(self) -> ComponentStatus:
        """
        Verify MT5/MetaAPI connection and terminal trading status.
        Ensures connectivity, permissions, and symbol tradability.
        """
        if not self.connector:
            res = ComponentStatus(
                status=HealthStatus.FAILED,
                message="MT5Connector not initialized",
                remedy="Initialization logic failed. Check application logs.",
            )
            self._update_gauge("mt5", res.status)
            return res

        if not self.connector._is_initialized:
            res = ComponentStatus(
                status=HealthStatus.FAILED,
                message="MT5 connection not initialized",
                remedy="Check MT5 credentials, path, and server in .env. Ensure MT5 terminal is running.",
            )
            self._update_gauge("mt5", res.status)
            return res

        # Check Circuit Breaker state (Self-healing monitoring)
        if self.connector.circuit_state == "OPEN":
            res = ComponentStatus(
                status=HealthStatus.DEGRADED,
                message="MT5 circuit breaker is OPEN (failing requests blocked)",
                remedy="Check network stability or broker API status. System will auto-recover in HALF_OPEN state.",
            )
            self._update_gauge("mt5", res.status)
            return res

        try:
            # 1. Account Info Check
            info = self.connector.get_account_info()
            if not info:
                res = ComponentStatus(
                    status=HealthStatus.FAILED,
                    message="MT5 failed to return account info",
                    remedy="Verify MT5 connection and credentials",
                )
                self._update_gauge("mt5", res.status)
                return res

            # 2. Terminal & Account Permissions
            status_info = self.connector.get_terminal_status()
            account_trade_allowed = info.get("trade_allowed", True)
            # MT5Connector.get_terminal_status already normalizes this to 'algo_trading'
            terminal_trade_allowed = status_info.get("algo_trading", True)

            # 3. Symbol Validation
            symbol = self.cfg.symbol
            symbol_props = self.connector.get_symbol_properties(symbol)

            messages = []
            overall_status = HealthStatus.HEALTHY
            remedies = []

            if not terminal_trade_allowed:
                messages.append("Algo Trading is DISABLED in terminal")
                remedies.append("Enable 'Algo Trading' button in MT5 terminal")
                # In LIVE mode, this is a critical failure
                overall_status = HealthStatus.FAILED if self.cfg.is_live else HealthStatus.DEGRADED

            if not account_trade_allowed:
                messages.append("Trading is DISABLED for this account by broker")
                remedies.append("Contact broker or check if account is read-only or has limited permissions")
                overall_status = HealthStatus.FAILED

            if not symbol_props:
                similar = self.connector.find_symbols(symbol[:3]) if len(symbol) >= 3 else []
                suggestion = f" (Did you mean: {', '.join(similar[:3])}?)" if similar else ""
                messages.append(f"Symbol '{symbol}' not found on server{suggestion}")
                remedies.append(f"Check SYMBOL in .env is exactly as it appears in MT5 Market Watch{suggestion}")
                overall_status = HealthStatus.FAILED
            elif not symbol_props.get("tradable", True):
                messages.append(f"Symbol '{symbol}' is not tradable (Market closed)")
                remedies.append("Wait for market open or use a symbol with active trading hours")
                overall_status = HealthStatus.DEGRADED

            if not messages:
                msg = "MT5 connection active and trading ready"
                if getattr(self.connector, "use_metaapi", False):
                    msg += " (via MetaAPI)"
                res = ComponentStatus(status=HealthStatus.HEALTHY, message=msg)
            else:
                res = ComponentStatus(
                    status=overall_status,
                    message=" | ".join(messages),
                    remedy="; ".join(remedies) if remedies else "N/A",
                )

        except Exception as e:
            logger.error("Health check - MT5 failure: %s", e)
            res = ComponentStatus(
                status=HealthStatus.FAILED,
                message=f"MT5 API call failed: {e!s}",
                remedy="Check MT5 terminal connectivity and network status",
            )

        self._update_gauge("mt5", res.status)
        return res

    def check_models(self) -> ComponentStatus:
        """
        Verify AI models are loaded and healthy.
        Ensures the loaded model matches the configured algorithm.
        """
        if not self.model:
            res = ComponentStatus(
                status=HealthStatus.FAILED,
                message="Model orchestrator not initialized",
                remedy="Initialization failure. Check model weight paths and ALGORITHM in .env",
            )
            self._update_gauge("models", res.status)
            return res

        algo = self.cfg.algorithm.lower()
        loaded = []
        status = HealthStatus.HEALTHY
        remedy = "N/A"

        # 1. Discover loaded components
        if getattr(self.model, "ppo_agent", None) is not None:
            loaded.append("ppo")
        if getattr(self.model, "lstm_model", None) is not None:
            loaded.append("lstm")
        if getattr(self.model, "dreamer_agent", None) is not None:
            loaded.append("dreamer")

        # Check for Transformer
        if (
            getattr(self.model, "transformer_model", None) is not None
            or self.model.__class__.__name__ == "TimeSeriesTransformer"
        ):
            loaded.append("transformer")

        # Fallback for individual wrappers
        if not loaded:
            class_name = self.model.__class__.__name__.lower()
            if "ppo" in class_name:
                loaded.append("ppo")
            elif "lstm" in class_name:
                loaded.append("lstm")
            elif "transformer" in class_name:
                loaded.append("transformer")
            elif "dreamer" in class_name:
                loaded.append("dreamer")
            elif hasattr(self.model, "predict"):
                loaded.append(class_name)

        # 2. Validate against configuration
        if algo == "ensemble":
            # Ensemble requires at least two of (ppo, lstm, dreamer) for full health
            # If some are missing but at least one is present, it's DEGRADED
            essential = {"ppo", "lstm", "dreamer"}
            present = essential.intersection(set(loaded))

            if not present:
                status = HealthStatus.FAILED
                msg = f"Ensemble algorithm configured but no base models ({', '.join(essential)}) loaded"
                remedy = f"Ensure model files for {', '.join(essential)} exist in models/trained/"
            elif len(present) < len(essential):
                status = HealthStatus.DEGRADED
                missing = essential - present
                msg = f"Ensemble DEGRADED: {', '.join(present)} active | Missing {', '.join(missing)}"
                remedy = f"Load missing components: {', '.join(missing)}"
            else:
                msg = f"Ensemble HEALTHY: All components ({', '.join(present)}) active"
        else:
            # Single algorithm check
            if algo not in loaded:
                status = HealthStatus.FAILED
                msg = f"Algorithm mismatch: Configured for '{algo}' but loaded '{', '.join(loaded) or 'None'}'"
                remedy = f"Update ALGORITHM in .env to match loaded model or provide weights for '{algo}'"
            else:
                msg = f"Model '{algo}' loaded and active"

        # 3. Performance Metrics Integration
        if status != HealthStatus.FAILED and hasattr(self.model, "get_health_metrics"):
            with contextlib.suppress(Exception):
                m = self.model.get_health_metrics()
                if m:
                    msg += f" | Performance: acc={m.get('accuracy', 0):.2f}, drift={m.get('drift', 0):.2f}"
                    # Check against thresholds if available in config
                    drift_limit = getattr(self.cfg, "model_drift_threshold", 0.3)
                    acc_floor = getattr(self.cfg, "model_accuracy_floor", 0.5)

                    if m.get("drift", 0) > drift_limit or m.get("accuracy", 1.0) < acc_floor:
                        status = HealthStatus.DEGRADED
                        msg += " (Threshold violation)"
                        remedy = "Retrain model or check for data drift in feature engineering"

        res = ComponentStatus(status=status, message=msg, remedy=remedy)
        self._update_gauge("models", res.status)
        return res

    def check_config(self) -> ComponentStatus:
        """Run startup configuration validator to ensure environment consistency."""
        validator = ConfigValidator(self.cfg)
        result = validator.validate()

        if result.success:
            if result.errors:
                msg = f"Valid with warnings: {'; '.join(e.message for e in result.errors)}"
                res = ComponentStatus(status=HealthStatus.DEGRADED, message=msg)
            else:
                res = ComponentStatus(status=HealthStatus.HEALTHY, message="Configuration is valid")
        else:
            critical = [e.message for e in result.errors if e.critical]
            res = ComponentStatus(
                status=HealthStatus.FAILED,
                message=f"Config invalid: {'; '.join(critical)}",
                remedy="Review .env and ensure all required variables are set correctly",
            )

        self._update_gauge("config", res.status)
        return res

    def check_disk_space(self, min_mb: int = 100) -> ComponentStatus:
        """Ensure the log directory has sufficient space for operational persistence."""
        logs_dir = self.cfg.logs_dir
        if not logs_dir.exists():
            try:
                logs_dir.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                res = ComponentStatus(status=HealthStatus.FAILED, message=f"Log dir error: {e}")
                self._update_gauge("disk", res.status)
                return res

        usage = shutil.disk_usage(logs_dir)
        free_mb = usage.free / (1024 * 1024)

        if free_mb < min_mb:
            res = ComponentStatus(
                status=HealthStatus.FAILED,
                message=f"Low disk: {free_mb:.1f}MB free",
                remedy="Clear old logs, increase disk quota, or check for large data files",
            )
        else:
            res = ComponentStatus(
                status=HealthStatus.HEALTHY, message=f"Disk space OK: {free_mb:.1f}MB free"
            )

        self._update_gauge("disk", res.status)
        return res

    def check_redis(self) -> ComponentStatus:
        """Verify Redis connectivity if configured (optional component)."""
        if not self.cfg.redis_url or not self.cfg.redis_url.get_secret_value():
            res = ComponentStatus(
                status=HealthStatus.HEALTHY, message="Redis not configured (Optional)"
            )
            self._update_gauge("redis", res.status)
            return res

        try:
            client = redis.from_url(self.cfg.redis_url.get_secret_value(), socket_timeout=2)
            if client.ping():
                res = ComponentStatus(status=HealthStatus.HEALTHY, message="Redis reachable")
            else:
                res = ComponentStatus(status=HealthStatus.DEGRADED, message="Redis ping failed")
        except Exception:
            res = ComponentStatus(status=HealthStatus.DEGRADED, message="Redis unreachable")

        self._update_gauge("redis", res.status)
        return res

    def check_audit_log(self) -> ComponentStatus:
        """Verify AuditLogger is initialized and active for traceability."""
        if not self.audit_logger:
            res = ComponentStatus(
                status=HealthStatus.FAILED,
                message="AuditLogger not initialized",
                remedy="Ensure database for audit log is accessible",
            )
        elif not self.audit_logger._initialized:
            res = ComponentStatus(
                status=HealthStatus.FAILED,
                message="AuditLogger not properly initialized",
                remedy="Check audit database connection and schema",
            )
        else:
            res = ComponentStatus(status=HealthStatus.HEALTHY, message="Audit trace active")

        self._update_gauge("audit_log", res.status)
        return res

    def get_full_report(self) -> HealthReport:
        """Aggregate all enterprise health checks into a unified report."""
        components = {
            "liveness": self.check_liveness(),
            "environment": self.check_environment(),
            "system_resources": self.check_system_resources(),
            "database": self.check_database(),
            "mt5": self.check_mt5(),
            "models": self.check_models(),
            "config": self.check_config(),
            "disk": self.check_disk_space(),
            "redis": self.check_redis(),
            "audit_log": self.check_audit_log(),
        }

        failed = any(c.status == HealthStatus.FAILED for c in components.values())
        degraded = any(c.status == HealthStatus.DEGRADED for c in components.values())
        overall = (
            HealthStatus.FAILED
            if failed
            else (HealthStatus.DEGRADED if degraded else HealthStatus.HEALTHY)
        )

        return HealthReport(
            status=overall,
            version=get_system_version(),
            environment=self.cfg.mode,
            components=components,
        )

    def startup_gate(self) -> HealthReport:
        """
        Critical Startup Gate: blocks application start if health is compromised.
        Aligned with Enterprise Release Standards and fail-fast policy.
        """
        report = self.get_full_report()
        if report.status == HealthStatus.FAILED:
            failed = [n for n, c in report.components.items() if c.status == HealthStatus.FAILED]
            msg = f"CRITICAL: Startup Health Gate FAILED. Components: {', '.join(failed)}"
            logger.critical(msg)
            if self.audit_logger:
                with contextlib.suppress(Exception):
                    self.audit_logger.log_operator_action(
                        operator="system",
                        action="startup_gate_failure",
                        reason=msg,
                        metadata={"failed": failed},
                    )
            # Raising RuntimeError blocks the trading engine start in main.py
            raise RuntimeError(msg)

        if report.status == HealthStatus.DEGRADED:
            warnings = [
                n for n, c in report.components.items() if c.status == HealthStatus.DEGRADED
            ]
            msg = f"Startup Health Gate PASSED with warnings in: {', '.join(warnings)}"
            logger.warning(msg)
            if self.audit_logger:
                with contextlib.suppress(Exception):
                    self.audit_logger.log("system", "startup_gate_warning", msg)
        else:
            logger.info("Startup Health Gate PASSED successfully")
            if self.audit_logger:
                with contextlib.suppress(Exception):
                    self.audit_logger.log(
                        "system", "startup_gate_success", "All health checks passed"
                    )

        return report


# --- API Interface ---

router = APIRouter(prefix="/health", tags=["health"])
_checker: Optional[HealthChecker] = None


def init_health_checker(
    config: TradingConfig,
    connector: MT5Connector,
    trade_logger: TradeLogger,
    model: Any,
    audit_logger: Optional[AuditLogger] = None,
) -> HealthChecker:
    """Initialize the global health checker instance."""
    global _checker
    _checker = HealthChecker(config, connector, trade_logger, model, audit_logger)
    return _checker


def get_health_checker() -> HealthChecker:
    """Retrieve the global health checker or return a default one if uninitialized."""
    global _checker
    if _checker is None:
        _checker = HealthChecker(get_config())
    return _checker


@router.get("/liveness", response_model=ComponentStatus)
async def liveness():
    """Liveness probe: lightweight process heartbeat."""
    return get_health_checker().check_liveness()


@router.get("/readiness", response_model=HealthReport)
async def readiness():
    """
    Readiness probe: check if the application is ready to handle trades.
    Returns 503 Service Unavailable if critical checks fail.
    """
    report = get_health_checker().get_full_report()
    if report.status == HealthStatus.FAILED:
        raise HTTPException(status_code=503, detail=jsonable_encoder(report))
    return report


@router.get("/full", response_model=HealthReport)
async def full():
    """Full enterprise health report for detailed diagnostics."""
    return get_health_checker().get_full_report()


def create_health_app() -> FastAPI:
    """Create the health monitoring micro-app with Prometheus integration."""
    app = FastAPI(title="MT5 Bot Health Monitoring", version=get_system_version())
    app.include_router(router)
    app.mount("/metrics", make_asgi_app())
    return app


__all__ = [
    "ComponentStatus",
    "HealthChecker",
    "HealthReport",
    "HealthStatus",
    "create_health_app",
    "get_health_checker",
    "init_health_checker",
    "router",
]

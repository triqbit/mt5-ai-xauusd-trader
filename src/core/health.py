"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/core/health.py
Enterprise-grade health check system for production monitoring.
Author : triqbit
License: MIT
"""

from __future__ import annotations

import logging
import platform
import shutil
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

import redis
from fastapi import APIRouter, FastAPI, HTTPException, status
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
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILED = "failed"


def get_system_version() -> str:
    """Utility to retrieve application version."""
    try:
        from src import __version__
        return __version__
    except ImportError:
        return "unknown"


class ComponentStatus(BaseModel):
    """Status of an individual system component."""
    status: HealthStatus
    message: str
    remedy: str = "N/A"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class HealthReport(BaseModel):
    """Aggregate health report containing status of all components."""
    status: HealthStatus
    version: str = "unknown"
    environment: str = "production"
    components: Dict[str, ComponentStatus]
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class HealthChecker:
    """
    Enterprise health checker for production monitoring and startup gating.
    Implements probes and dependency checks aligned with SLO targets.
    """

    def __init__(
        self,
        config: TradingConfig,
        connector: Optional[MT5Connector] = None,
        trade_logger: Optional[TradeLogger] = None,
        model: Optional[Any] = None,
        audit_logger: Optional[AuditLogger] = None,
    ) -> None:
        self.cfg = config
        self.connector = connector
        self.trade_logger = trade_logger
        self.model = model
        self.audit_logger = audit_logger

    def _update_gauge(self, component: str, status: HealthStatus) -> None:
        """Update Prometheus health gauge for a component."""
        val = 1.0 if status == HealthStatus.HEALTHY else (0.5 if status == HealthStatus.DEGRADED else 0.0)
        HEALTH_GAUGES.labels(component=component).set(val)

    def check_liveness(self) -> ComponentStatus:
        """
        Liveness probe: is the process running and responsive?
        Basic check that doesn't depend on external systems.
        """
        res = ComponentStatus(status=HealthStatus.HEALTHY, message="Application process is active")
        self._update_gauge("liveness", res.status)
        return res

    def check_environment(self) -> ComponentStatus:
        """Report on the execution environment (OS, Python, Hardware)."""
        py_ver = platform.python_version()
        os_info = f"{platform.system()} {platform.release()}"

        hardware = "CPU"
        try:
            import torch
            if torch.cuda.is_available():
                hardware = f"GPU (CUDA: {torch.cuda.get_device_name(0)})"
            elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                hardware = "GPU (MPS)"
        except ImportError:
            hardware = "CPU (PyTorch not installed)"

        msg = f"Python {py_ver} on {os_info} | Hardware: {hardware}"
        res = ComponentStatus(status=HealthStatus.HEALTHY, message=msg)
        self._update_gauge("environment", res.status)
        return res

    def check_database(self) -> ComponentStatus:
        """Verify primary database reachability."""
        if not self.trade_logger:
            res = ComponentStatus(status=HealthStatus.FAILED, message="TradeLogger not initialized", remedy="Ensure DB_URL is valid in .env")
            self._update_gauge("database", res.status)
            return res

        try:
            with self.trade_logger.engine.connect() as conn:
                try:
                    conn.execute(self.trade_logger.engine.dialect.do_ping(conn.connection))
                except (AttributeError, Exception):
                    conn.execute(text("SELECT 1"))
            res = ComponentStatus(status=HealthStatus.HEALTHY, message="Database reachable")
        except Exception as e:
            logger.error("Health check - Database failure: %s", e)
            res = ComponentStatus(status=HealthStatus.FAILED, message=f"Database unreachable: {e!s}", remedy="Check database service and connection string")

        self._update_gauge("database", res.status)
        return res

    def check_mt5(self) -> ComponentStatus:
        """Verify MT5/MetaAPI connection and terminal trading status."""
        if not self.connector:
            res = ComponentStatus(status=HealthStatus.FAILED, message="MT5Connector not initialized")
            self._update_gauge("mt5", res.status)
            return res

        if not self.connector._is_initialized:
            res = ComponentStatus(status=HealthStatus.FAILED, message="MT5 connection not initialized", remedy="Check credentials and network")
            self._update_gauge("mt5", res.status)
            return res

        try:
            # 1. Account Info Check
            info = self.connector.get_account_info()
            if not info:
                res = ComponentStatus(status=HealthStatus.FAILED, message="MT5 failed to return account info")
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
                remedies.append("Enable 'Algo Trading' button in MT5")
                overall_status = HealthStatus.DEGRADED

            if not account_trade_allowed:
                messages.append("Trading is DISABLED for this account by broker")
                remedies.append("Contact broker or check if account is read-only")
                overall_status = HealthStatus.FAILED

            if not symbol_props:
                similar = self.connector.find_symbols(symbol[:3]) if len(symbol) >= 3 else []
                suggestion = f" (Did you mean: {', '.join(similar[:3])}?)" if similar else ""
                messages.append(f"Symbol '{symbol}' not found on server{suggestion}")
                remedies.append(f"Check SYMBOL in .env{suggestion}")
                overall_status = HealthStatus.FAILED
            elif not symbol_props.get("tradable", True):
                messages.append(f"Symbol '{symbol}' is not tradable (Market closed)")
                remedies.append("Wait for market open")
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
                    remedy="; ".join(remedies) if remedies else "N/A"
                )

        except Exception as e:
            logger.error("Health check - MT5 failure: %s", e)
            res = ComponentStatus(status=HealthStatus.FAILED, message=f"MT5 API call failed: {e!s}")

        self._update_gauge("mt5", res.status)
        return res

    def check_models(self) -> ComponentStatus:
        """Verify AI models are loaded and healthy."""
        if not self.model:
            res = ComponentStatus(status=HealthStatus.FAILED, message="Model orchestrator not initialized")
            self._update_gauge("models", res.status)
            return res

        loaded = []
        # Check EnsembleModel components (Standard attributes)
        if getattr(self.model, "ppo_agent", None) is not None:
            loaded.append("PPO")
        if getattr(self.model, "lstm_model", None) is not None:
            loaded.append("LSTM")
        if getattr(self.model, "dreamer_agent", None) is not None:
            loaded.append("Dreamer")

        # Check for individual model wrapper
        if not loaded and getattr(self.model, "model", None) is not None:
            loaded.append(self.model.__class__.__name__)

        if not loaded:
            res = ComponentStatus(status=HealthStatus.FAILED, message="No models loaded in memory", remedy="Ensure model weights exist in models/trained/")
        else:
            msg = f"Models loaded: {', '.join(loaded)}"
            # Optional: integration with model performance tracking
            if hasattr(self.model, "get_health_metrics"):
                try:
                    m = self.model.get_health_metrics()
                    msg += f" | Health: acc={m.get('accuracy', 0):.2f}, drift={m.get('drift', 0):.2f}"
                except Exception: pass
            res = ComponentStatus(status=HealthStatus.HEALTHY, message=msg)

        self._update_gauge("models", res.status)
        return res

    def check_config(self) -> ComponentStatus:
        """Run startup configuration validator."""
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
            res = ComponentStatus(status=HealthStatus.FAILED, message=f"Config invalid: {'; '.join(critical)}", remedy="Review .env and validation output")

        self._update_gauge("config", res.status)
        return res

    def check_disk_space(self, min_mb: int = 100) -> ComponentStatus:
        """Ensure log directory has sufficient space."""
        logs_dir = self.cfg.logs_dir
        if not logs_dir.exists():
            try: logs_dir.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                res = ComponentStatus(status=HealthStatus.FAILED, message=f"Log dir error: {e}")
                self._update_gauge("disk", res.status)
                return res

        usage = shutil.disk_usage(logs_dir)
        free_mb = usage.free / (1024 * 1024)

        if free_mb < min_mb:
            res = ComponentStatus(status=HealthStatus.FAILED, message=f"Low disk: {free_mb:.1f}MB free", remedy="Clear old logs or increase disk quota")
        else:
            res = ComponentStatus(status=HealthStatus.HEALTHY, message=f"Disk space OK: {free_mb:.1f}MB free")

        self._update_gauge("disk", res.status)
        return res

    def check_redis(self) -> ComponentStatus:
        """Verify Redis connectivity if configured."""
        if not self.cfg.redis_url:
            res = ComponentStatus(status=HealthStatus.DEGRADED, message="Redis not configured (Optional)")
            self._update_gauge("redis", res.status)
            return res

        try:
            client = redis.from_url(self.cfg.redis_url, socket_timeout=2)
            if client.ping():
                res = ComponentStatus(status=HealthStatus.HEALTHY, message="Redis reachable")
            else:
                res = ComponentStatus(status=HealthStatus.DEGRADED, message="Redis ping failed")
        except Exception:
            res = ComponentStatus(status=HealthStatus.DEGRADED, message="Redis unreachable")

        self._update_gauge("redis", res.status)
        return res

    def check_audit_log(self) -> ComponentStatus:
        """Verify AuditLogger is initialized."""
        if not self.audit_logger or not self.audit_logger._initialized:
            res = ComponentStatus(status=HealthStatus.FAILED, message="AuditLogger inactive", remedy="Check audit database connection")
        else:
            res = ComponentStatus(status=HealthStatus.HEALTHY, message="Audit trace active")

        self._update_gauge("audit_log", res.status)
        return res

    def get_full_report(self) -> HealthReport:
        """Aggregate all enterprise health checks."""
        components = {
            "liveness": self.check_liveness(),
            "environment": self.check_environment(),
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
        overall = HealthStatus.FAILED if failed else (HealthStatus.DEGRADED if degraded else HealthStatus.HEALTHY)

        return HealthReport(
            status=overall,
            version=get_system_version(),
            environment=self.cfg.mode,
            components=components,
        )

    def startup_gate(self) -> HealthReport:
        """
        Critical Startup Gate: blocks application start if health is compromised.
        Aligned with Enterprise Release Standards.
        """
        report = self.get_full_report()
        if report.status == HealthStatus.FAILED:
            failed = [n for n, c in report.components.items() if c.status == HealthStatus.FAILED]
            msg = f"CRITICAL: Startup Health Gate FAILED. Components: {', '.join(failed)}"
            logger.critical(msg)
            if self.audit_logger:
                try:
                    self.audit_logger.log_operator_action(
                        operator="system", action="startup_gate_failure", reason=msg, metadata={"failed": failed}
                    )
                except Exception: pass
            raise RuntimeError(msg)

        if report.status == HealthStatus.DEGRADED:
            warnings = [n for n, c in report.components.items() if c.status == HealthStatus.DEGRADED]
            msg = f"Startup Health Gate PASSED with warnings in: {', '.join(warnings)}"
            logger.warning(msg)
            if self.audit_logger:
                try:
                    self.audit_logger.log("system", "startup_gate_warning", msg)
                except Exception: pass
        else:
            logger.info("Startup Health Gate PASSED successfully")
            if self.audit_logger:
                try:
                    self.audit_logger.log("system", "startup_gate_success", "All health checks passed")
                except Exception: pass

        return report


# --- API Interface ---

router = APIRouter(prefix="/health", tags=["health"])
_checker: Optional[HealthChecker] = None

def init_health_checker(config: TradingConfig, connector: MT5Connector, trade_logger: TradeLogger, model: Any, audit_logger: Optional[AuditLogger] = None) -> HealthChecker:
    global _checker
    _checker = HealthChecker(config, connector, trade_logger, model, audit_logger)
    return _checker

def get_health_checker() -> HealthChecker:
    global _checker
    if _checker is None: _checker = HealthChecker(get_config())
    return _checker

@router.get("/liveness", response_model=ComponentStatus)
async def liveness():
    """Liveness probe: process heartbeat."""
    return get_health_checker().check_liveness()

@router.get("/readiness", response_model=HealthReport)
async def readiness():
    """Readiness probe: check all dependencies."""
    report = get_health_checker().get_full_report()
    if report.status == HealthStatus.FAILED:
        raise HTTPException(status_code=503, detail=jsonable_encoder(report))
    return report

@router.get("/full", response_model=HealthReport)
async def full():
    """Full enterprise health report."""
    return get_health_checker().get_full_report()

def create_health_app() -> FastAPI:
    """Create the health monitoring micro-app."""
    app = FastAPI(title="MT5 Bot Health Monitoring", version=get_system_version())
    app.include_router(router)
    app.mount("/metrics", make_asgi_app())
    return app

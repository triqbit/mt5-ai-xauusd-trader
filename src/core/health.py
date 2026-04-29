"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/core/health.py
Production-grade health check system and startup gates.
Author : triqbit
License: MIT
"""
from __future__ import annotations

import os
import shutil
import sys
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog
from pydantic import BaseModel, Field

from src.core.config import TradingConfig

logger = structlog.get_logger(__name__)


class HealthStatus(str, Enum):
    """Standardized health status levels."""

    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    FAILED = "FAILED"


class ComponentHealth(BaseModel):
    """Health status for a specific system component."""

    status: HealthStatus
    message: str
    details: Dict[str, Any] = Field(default_factory=dict)


class HealthReport(BaseModel):
    """Aggregated health report for the entire system."""

    overall_status: HealthStatus
    components: Dict[str, ComponentHealth]


class HealthChecker:
    """
    Maintains system liveness and readiness probes.
    Used for startup gates and runtime monitoring.
    """

    def __init__(self, config: TradingConfig) -> None:
        self.cfg = config

    def check_mt5(self, connector: Any) -> ComponentHealth:
        """Verify MT5 terminal connectivity."""
        try:
            # We use initialize() which is the primary connection method
            is_connected = connector.initialize()
            if is_connected:
                # Check account info to ensure session is active
                acc = connector.get_account_info()
                if acc:
                    return ComponentHealth(
                        status=HealthStatus.HEALTHY,
                        message="MT5 Connected",
                        details={"login": acc.get("login"), "server": acc.get("server")},
                    )
                return ComponentHealth(
                    status=HealthStatus.DEGRADED,
                    message="MT5 Initialized but no account info",
                )
            return ComponentHealth(
                status=HealthStatus.FAILED,
                message="MT5 terminal connection failed",
            )
        except Exception as e:
            return ComponentHealth(
                status=HealthStatus.FAILED,
                message=f"MT5 probe exception: {str(e)}",
            )

    def check_database(self, logger_db: Any) -> ComponentHealth:
        """Verify database connectivity and schema availability."""
        try:
            # Simple query to verify engine/session
            with logger_db.Session() as session:
                from sqlalchemy import text

                session.execute(text("SELECT 1"))
            return ComponentHealth(status=HealthStatus.HEALTHY, message="Database reachable")
        except Exception as e:
            return ComponentHealth(
                status=HealthStatus.FAILED,
                message=f"Database probe failed: {str(e)}",
            )

    def check_models(self, model_dir: Optional[Path] = None) -> ComponentHealth:
        """Verify existence of critical model files."""
        # Use model_dir if provided, otherwise fall back to config
        base_dir = model_dir or self.cfg.model_path.parent

        # Check specific files expected by main.py
        ppo_file = base_dir / "ppo_xauusd.zip"
        lstm_file = base_dir / "lstm_xauusd.pt"

        missing = []
        if not ppo_file.exists():
            missing.append(str(ppo_file))
        if not lstm_file.exists():
            missing.append(str(lstm_file))

        if not missing:
            return ComponentHealth(status=HealthStatus.HEALTHY, message="All models present")
        elif len(missing) < 2:
            return ComponentHealth(
                status=HealthStatus.DEGRADED,
                message="Partial models found",
                details={"missing": missing},
            )
        return ComponentHealth(
            status=HealthStatus.FAILED,
            message="No models found",
            details={"missing": missing},
        )

    def check_disk_space(self, min_gb: float = 1.0) -> ComponentHealth:
        """Verify sufficient disk space for logs and DB."""
        total, used, free = shutil.disk_usage(os.getcwd())
        free_gb = free / (2**30)
        if free_gb > min_gb:
            return ComponentHealth(
                status=HealthStatus.HEALTHY,
                message=f"Disk space OK ({free_gb:.2f} GB free)",
            )
        return ComponentHealth(
            status=HealthStatus.DEGRADED,
            message=f"Low disk space: {free_gb:.2f} GB free",
        )

    def run_startup_gate(self, connector: Any, logger_db: Any, model_dir: Optional[Path] = None) -> bool:
        """
        Hard enforcement of system readiness.
        If in live/demo mode, exits on FAILED critical components.
        """
        logger.info("Running startup health gate...")
        report = self.get_full_report(connector, logger_db, model_dir)

        critical_failed = False
        # Critical dependencies for live/demo trading
        critical_components = ["mt5", "database"]

        for comp in critical_components:
            if report.components[comp].status == HealthStatus.FAILED:
                logger.critical(
                    "STARTUP GATE FAILED",
                    component=comp,
                    status=report.components[comp].status,
                    message=report.components[comp].message,
                )
                critical_failed = True

        if critical_failed and self.cfg.mode in ("live", "demo"):
            logger.error("System critical failure in mode. Aborting.", mode=self.cfg.mode)
            sys.exit(1)

        if report.overall_status == HealthStatus.HEALTHY:
            logger.info("Startup gate PASSED - System is HEALTHY")
        else:
            logger.warning("Startup gate PASSED with warnings", status=report.overall_status)

        return not critical_failed

    def get_full_report(self, connector: Any, logger_db: Any, model_dir: Optional[Path] = None) -> HealthReport:
        """Aggregate all health probes into a single report."""
        components = {
            "mt5": self.check_mt5(connector),
            "database": self.check_database(logger_db),
            "models": self.check_models(model_dir),
            "disk": self.check_disk_space(),
        }

        # Determine overall status
        statuses = [c.status for c in components.values()]
        if HealthStatus.FAILED in statuses:
            overall = HealthStatus.FAILED
        elif HealthStatus.DEGRADED in statuses:
            overall = HealthStatus.DEGRADED
        else:
            overall = HealthStatus.HEALTHY

        return HealthReport(overall_status=overall, components=components)

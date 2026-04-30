"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/core/health.py
Enterprise-grade health monitoring and startup validation.
Author : triqbit
License: MIT
"""

from __future__ import annotations

import logging
import shutil
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field
from sqlalchemy import text

from src.core.config import TradingConfig
from src.trading.mt5_connector import MT5Connector

logger = logging.getLogger(__name__)


class HealthStatus(str, Enum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    FAILED = "FAILED"


class ComponentHealth(BaseModel):
    """Health status of an individual system component."""

    status: HealthStatus
    message: str
    details: Dict[str, Any] = Field(default_factory=dict)


class SystemHealth(BaseModel):
    """Aggregated health report for the entire system."""

    overall_status: HealthStatus
    components: Dict[str, ComponentHealth]
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class HealthCheck:
    """
    Enterprise health monitoring suite.
    Performs deep validation of system dependencies and environment.
    """

    def __init__(self, config: TradingConfig, connector: Optional[MT5Connector] = None) -> None:
        self.cfg = config
        self.connector = connector

    def check_disk_space(self, min_gb: float = 1.0) -> ComponentHealth:
        """Verify sufficient disk space for logs and database."""
        path = Path(self.cfg.logs_dir).parent
        _, _, free = shutil.disk_usage(path)
        free_gb = free / (2**30)

        status = HealthStatus.HEALTHY if free_gb > min_gb else HealthStatus.FAILED
        return ComponentHealth(
            status=status,
            message=f"Free disk space: {free_gb:.2f} GB",
            details={"free_gb": free_gb, "threshold_gb": min_gb},
        )

    def check_database(self) -> ComponentHealth:
        """Verify database connectivity and responsiveness."""
        from src.core.trade_logger import TradeLogger

        try:
            # Re-use TradeLogger to test connection
            logger_db = TradeLogger(db_url=self.cfg.database_url)
            with logger_db.Session() as session:
                # Use sqlalchemy.text() for compliance and security
                session.execute(text("SELECT 1"))
            return ComponentHealth(
                status=HealthStatus.HEALTHY, message="Database connection verified"
            )
        except Exception as e:
            logger.error("Database health check failed: %s", e)
            return ComponentHealth(
                status=HealthStatus.FAILED,
                message=f"Database connection failed: {e!s}",
            )

    def check_mt5(self) -> ComponentHealth:
        """Verify MetaTrader 5 connectivity."""
        if not self.connector:
            return ComponentHealth(
                status=HealthStatus.DEGRADED, message="MT5 connector not provided"
            )

        if self.connector._is_initialized:
            # Check if we can get a tick to verify real connection
            tick = self.connector.get_tick(self.cfg.symbol)
            if tick.get("ask", 0) > 0:
                return ComponentHealth(status=HealthStatus.HEALTHY, message="MT5 connection active")
            return ComponentHealth(
                status=HealthStatus.DEGRADED, message="MT5 connected but no market data"
            )

        return ComponentHealth(status=HealthStatus.FAILED, message="MT5 not initialized")

    def check_models(self) -> ComponentHealth:
        """Verify model files exist and are readable."""
        model_path = Path(self.cfg.model_path)
        if model_path.exists():
            return ComponentHealth(
                status=HealthStatus.HEALTHY,
                message=f"Model found at {model_path}",
                details={"size_bytes": model_path.stat().st_size},
            )
        return ComponentHealth(
            status=HealthStatus.FAILED,
            message=f"Model file missing: {model_path}",
        )

    def run_all(self) -> SystemHealth:
        """Execute all health checks and aggregate results."""
        components = {
            "disk": self.check_disk_space(),
            "database": self.check_database(),
            "mt5": self.check_mt5(),
            "models": self.check_models(),
        }

        # If any critical component failed, system is FAILED
        # MT5 is critical for live/demo, but model might be missing during training
        overall = HealthStatus.HEALTHY
        if any(c.status == HealthStatus.FAILED for c in components.values()):
            overall = HealthStatus.FAILED
        elif any(c.status == HealthStatus.DEGRADED for c in components.values()):
            overall = HealthStatus.DEGRADED

        report = SystemHealth(overall_status=overall, components=components)
        logger.info("System Health Report: %s", report.overall_status)
        return report


def run_health_gate(config: TradingConfig, connector: Optional[MT5Connector] = None) -> bool:
    """
    Mandatory startup gate.
    Returns True if system is healthy or degraded (allowable), False if FAILED.
    """
    checker = HealthCheck(config, connector)
    report = checker.run_all()

    if report.overall_status == HealthStatus.FAILED:
        print("\n❌ SYSTEM HEALTH CHECK FAILED")
        for name, comp in report.components.items():
            if comp.status == HealthStatus.FAILED:
                print(f"  - {name}: {comp.message}")
        return False

    if report.overall_status == HealthStatus.DEGRADED:
        print("\n⚠️ SYSTEM HEALTH DEGRADED (Continuing...)")
        for name, comp in report.components.items():
            if comp.status == HealthStatus.DEGRADED:
                print(f"  - {name}: {comp.message}")

    return True

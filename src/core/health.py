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
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Optional

from pydantic import BaseModel, Field
from sqlalchemy import text

from src.core.config import TradingConfig
from src.core.trade_logger import TradeLogger
from src.trading.mt5_connector import MT5Connector

logger = logging.getLogger(__name__)


class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILED = "failed"


class ComponentStatus(BaseModel):
    status: HealthStatus
    message: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    details: Optional[Dict[str, str]] = None


class HealthReport(BaseModel):
    status: HealthStatus
    overall_message: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    components: Dict[str, ComponentStatus]


class HealthChecker:
    """
    Orchestrates health checks for all system components.
    """

    def __init__(self, config: TradingConfig) -> None:
        self.cfg = config

    def get_liveness(self) -> ComponentStatus:
        """Simple liveness probe - application is running."""
        return ComponentStatus(
            status=HealthStatus.HEALTHY,
            message="Application is responsive",
        )

    def check_database(self, trade_logger: TradeLogger) -> ComponentStatus:
        """Verify database connectivity."""
        try:
            with trade_logger.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return ComponentStatus(status=HealthStatus.HEALTHY, message="Database reachable")
        except Exception as e:
            logger.error("Health check: Database unreachable: %s", e)
            return ComponentStatus(
                status=HealthStatus.FAILED,
                message=f"Database unreachable: {e!s}",
            )

    def check_mt5(self, connector: MT5Connector) -> ComponentStatus:
        """Verify MT5 connection status."""
        if connector._is_initialized:
            # Optionally perform a light operation like getting account info
            try:
                acc = connector.get_account_info()
                if acc:
                    return ComponentStatus(
                        status=HealthStatus.HEALTHY,
                        message="MT5 connection alive",
                        details={"login": str(acc.get("login"))},
                    )
                return ComponentStatus(
                    status=HealthStatus.DEGRADED,
                    message="MT5 initialized but returned empty account info",
                )
            except Exception as e:
                return ComponentStatus(
                    status=HealthStatus.FAILED,
                    message=f"MT5 connectivity check failed: {e!s}",
                )
        return ComponentStatus(status=HealthStatus.FAILED, message="MT5 connector not initialized")

    def check_models(self) -> ComponentStatus:
        """Verify model file existence."""
        if self.cfg.model_path.exists():
            return ComponentStatus(
                status=HealthStatus.HEALTHY,
                message=f"Model file found at {self.cfg.model_path}",
            )
        return ComponentStatus(
            status=HealthStatus.FAILED,
            message=f"Model file missing at {self.cfg.model_path}",
        )

    def check_config(self) -> ComponentStatus:
        """Validate critical configuration fields."""
        missing = []
        if not self.cfg.mt5_password:
            missing.append("MT5_PASSWORD")
        if not self.cfg.mt5_server:
            missing.append("MT5_SERVER")

        if missing:
            return ComponentStatus(
                status=HealthStatus.FAILED,
                message=f"Critical config missing: {', '.join(missing)}",
            )
        return ComponentStatus(status=HealthStatus.HEALTHY, message="Config validation passed")

    def check_disk_space(self, min_gb: float = 1.0) -> ComponentStatus:
        """Verify log directory has sufficient space."""
        logs_dir = self.cfg.logs_dir
        if not logs_dir.exists():
            try:
                logs_dir.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                return ComponentStatus(
                    status=HealthStatus.FAILED,
                    message=f"Cannot create logs directory: {e!s}",
                )

        _, _, free = shutil.disk_usage(logs_dir)
        free_gb = free / (1024**3)

        if free_gb < min_gb:
            return ComponentStatus(
                status=HealthStatus.DEGRADED,
                message=f"Low disk space: {free_gb:.2f} GB free",
            )
        return ComponentStatus(
            status=HealthStatus.HEALTHY,
            message=f"Sufficient disk space: {free_gb:.2f} GB free",
        )

    def get_readiness(
        self,
        connector: MT5Connector,
        trade_logger: TradeLogger,
    ) -> HealthReport:
        """Aggregated readiness probe."""
        components = {
            "database": self.check_database(trade_logger),
            "mt5": self.check_mt5(connector),
            "models": self.check_models(),
            "config": self.check_config(),
            "disk": self.check_disk_space(),
        }

        failed_components = [
            name for name, res in components.items() if res.status == HealthStatus.FAILED
        ]
        degraded_components = [
            name for name, res in components.items() if res.status == HealthStatus.DEGRADED
        ]

        if failed_components:
            status = HealthStatus.FAILED
            msg = f"Critical health failure in: {', '.join(failed_components)}"
        elif degraded_components:
            status = HealthStatus.DEGRADED
            msg = f"Health degraded in: {', '.join(degraded_components)}"
        else:
            status = HealthStatus.HEALTHY
            msg = "System is ready"

        return HealthReport(
            status=status,
            overall_message=msg,
            components=components,
        )


def startup_health_gate(
    config: TradingConfig,
    connector: MT5Connector,
    trade_logger: TradeLogger,
) -> None:
    """
    Enforce health checks at startup.
    Raises RuntimeError if critical checks fail.
    """
    checker = HealthChecker(config)
    report = checker.get_readiness(connector, trade_logger)

    if report.status == HealthStatus.FAILED:
        logger.critical("STARTUP HEALTH GATE FAILED: %s", report.overall_message)
        for comp, status in report.components.items():
            if status.status == HealthStatus.FAILED:
                logger.critical(" - %s: %s", comp.upper(), status.message)
        raise RuntimeError(f"Startup health check failed: {report.overall_message}")

    logger.info("Startup health gate passed: %s", report.overall_message)

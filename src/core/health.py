"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/core/health.py
Enterprise-grade health check system for production monitoring.
Author : triqbit
License: MIT
"""
from __future__ import annotations

import logging
import os
import shutil
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field
from sqlalchemy import text

from src.core.config import TradingConfig
from src.core.trade_logger import TradeLogger
from src.models.ensemble import EnsembleModel
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
    details: Optional[Dict[str, Any]] = None


class HealthReport(BaseModel):
    status: HealthStatus
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    components: Dict[str, ComponentStatus]


class HealthCheckSystem:
    """
    Enterprise health check system for the trading bot.
    Handles liveness, readiness, and deep dependency validation.
    """

    def __init__(
        self,
        config: TradingConfig,
        connector: Optional[MT5Connector] = None,
        trade_logger: Optional[TradeLogger] = None,
        model: Optional[EnsembleModel] = None,
    ) -> None:
        self.cfg = config
        self.connector = connector
        self.trade_logger = trade_logger
        self.model = model

    def check_liveness(self) -> ComponentStatus:
        """Basic check to see if the process is alive."""
        return ComponentStatus(status=HealthStatus.HEALTHY, message="Application is running")

    def check_config(self) -> ComponentStatus:
        """Validate critical configuration parameters."""
        try:
            # Pydantic already validates on init, but we can do extra checks here
            if self.cfg.is_live and os.getenv("CONFIRM_LIVE_TRADING") != "true":
                return ComponentStatus(
                    status=HealthStatus.FAILED,
                    message="LIVE mode active but CONFIRM_LIVE_TRADING not set",
                )
            return ComponentStatus(status=HealthStatus.HEALTHY, message="Configuration is valid")
        except Exception as e:
            return ComponentStatus(status=HealthStatus.FAILED, message=f"Config check failed: {e}")

    def check_database(self) -> ComponentStatus:
        """Verify database connectivity."""
        if not self.trade_logger:
            return ComponentStatus(status=HealthStatus.FAILED, message="TradeLogger not initialized")
        try:
            with self.trade_logger.Session() as session:
                session.execute(text("SELECT 1"))
            return ComponentStatus(status=HealthStatus.HEALTHY, message="Database reachable")
        except Exception as e:
            return ComponentStatus(status=HealthStatus.FAILED, message=f"Database unreachable: {e}")

    def check_mt5(self) -> ComponentStatus:
        """Verify MT5 terminal or MetaAPI connection."""
        if not self.connector:
            return ComponentStatus(
                status=HealthStatus.FAILED, message="MT5Connector not initialized"
            )

        if self.connector._is_initialized:
            return ComponentStatus(status=HealthStatus.HEALTHY, message="MT5 connection alive")
        else:
            return ComponentStatus(status=HealthStatus.FAILED, message="MT5 not connected")

    def check_models(self) -> ComponentStatus:
        """Verify that at least one model is loaded and ready."""
        if not self.model:
            return ComponentStatus(
                status=HealthStatus.FAILED, message="EnsembleModel not initialized"
            )

        loaded_models = []
        if self.model._ppo_model is not None:
            loaded_models.append("PPO")
        if self.model.lstm_model is not None:
            loaded_models.append("LSTM")

        if not loaded_models:
            return ComponentStatus(status=HealthStatus.FAILED, message="No models loaded")

        return ComponentStatus(
            status=HealthStatus.HEALTHY,
            message=f"Models loaded: {', '.join(loaded_models)}",
            details={"loaded": loaded_models},
        )

    def check_disk_space(self) -> ComponentStatus:
        """Ensure sufficient disk space in log directory."""
        log_dir = self.cfg.logs_dir
        if not log_dir.exists():
            try:
                log_dir.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                return ComponentStatus(
                    status=HealthStatus.FAILED, message=f"Cannot create logs dir: {e}"
                )

        total, used, free = shutil.disk_usage(log_dir)
        free_gb = free / (2**30)

        if free_gb < 0.5:  # Require at least 500MB
            return ComponentStatus(
                status=HealthStatus.FAILED,
                message=f"Low disk space: {free_gb:.2f} GB free",
                details={"free_gb": free_gb},
            )
        elif free_gb < 1.0:
            return ComponentStatus(
                status=HealthStatus.DEGRADED,
                message=f"Moderate disk space: {free_gb:.2f} GB free",
                details={"free_gb": free_gb},
            )

        return ComponentStatus(
            status=HealthStatus.HEALTHY,
            message=f"Disk space OK: {free_gb:.2f} GB free",
            details={"free_gb": free_gb},
        )

    def get_readiness_report(self) -> HealthReport:
        """Generate a full health report of all components."""
        components = {
            "liveness": self.check_liveness(),
            "config": self.check_config(),
            "database": self.check_database(),
            "mt5": self.check_mt5(),
            "models": self.check_models(),
            "disk": self.check_disk_space(),
        }

        # Overall status: FAILED if any critical component is FAILED
        # DEGRADED if no FAILED but some DEGRADED
        if any(c.status == HealthStatus.FAILED for c in components.values()):
            overall = HealthStatus.FAILED
        elif any(c.status == HealthStatus.DEGRADED for c in components.values()):
            overall = HealthStatus.DEGRADED
        else:
            overall = HealthStatus.HEALTHY

        return HealthReport(status=overall, components=components)


def run_startup_gate(
    config: TradingConfig,
    connector: MT5Connector,
    trade_logger: TradeLogger,
    model: EnsembleModel,
) -> None:
    """
    Executes a mandatory startup health gate.
    Blocks application execution if critical health checks fail.
    """
    health = HealthCheckSystem(
        config=config,
        connector=connector,
        trade_logger=trade_logger,
        model=model,
    )

    report = health.get_readiness_report()

    if report.status == HealthStatus.FAILED:
        logger.critical("Startup health gate FAILED!")
        for name, comp in report.components.items():
            if comp.status == HealthStatus.FAILED:
                logger.error("Critical Failure [%s]: %s", name, comp.message)

        # In a real enterprise app, we exit with error code
        print("\nFATAL: Startup health gate failed. Check logs for details.")
        import sys
        sys.exit(1)

    logger.info("Startup health gate PASSED | status=%s", report.status)

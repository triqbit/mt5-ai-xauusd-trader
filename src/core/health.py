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
import sys
import time
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field
from sqlalchemy import text

from src.core.config import TradingConfig
from src.core.trade_logger import TradeLogger
from src.trading.mt5_connector import MT5Connector

try:
    from src.models.ensemble import EnsembleModel
    MODELS_AVAILABLE = True
except ImportError:
    MODELS_AVAILABLE = False
    EnsembleModel = Any  # type: ignore
from src import __version__

logger = logging.getLogger(__name__)

class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILED = "failed"

class ComponentStatus(BaseModel):
    status: HealthStatus
    message: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    details: Dict[str, Any] = Field(default_factory=dict)

class HealthCheckResponse(BaseModel):
    status: HealthStatus
    version: str = __version__
    uptime_seconds: float
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    components: Dict[str, ComponentStatus]

class HealthChecker:
    """
    Orchestrates health checks across all system components.
    """
    def __init__(
        self,
        cfg: TradingConfig,
        connector: Optional[MT5Connector] = None,
        trade_logger: Optional[TradeLogger] = None,
        model: Optional[EnsembleModel] = None,
    ) -> None:
        self.cfg = cfg
        self.connector = connector
        self.trade_logger = trade_logger
        self.model = model
        self.start_time = time.time()

    def check_liveness(self) -> ComponentStatus:
        """Is the application process alive?"""
        return ComponentStatus(status=HealthStatus.HEALTHY, message="Application is running")

    def check_readiness(self) -> ComponentStatus:
        """Is the application ready to handle trades?"""
        # Readiness means all critical components are healthy
        db = self.check_database()
        mt5 = self.check_mt5()
        models = self.check_models()

        if db.status == HealthStatus.FAILED or mt5.status == HealthStatus.FAILED or models.status == HealthStatus.FAILED:
            return ComponentStatus(status=HealthStatus.FAILED, message="Not ready: critical dependencies failed")

        return ComponentStatus(status=HealthStatus.HEALTHY, message="Ready")

    def check_database(self) -> ComponentStatus:
        """Verify database connectivity."""
        if not self.trade_logger:
            return ComponentStatus(status=HealthStatus.FAILED, message="TradeLogger not initialized")
        try:
            with self.trade_logger.Session() as session:
                session.execute(text("SELECT 1"))
            return ComponentStatus(status=HealthStatus.HEALTHY, message="Database reachable")
        except Exception as e:
            return ComponentStatus(status=HealthStatus.FAILED, message=f"Database unreachable: {e!s}")

    def check_mt5(self) -> ComponentStatus:
        """Verify MT5 connection."""
        if not self.connector:
            return ComponentStatus(status=HealthStatus.FAILED, message="MT5Connector not initialized")

        if self.connector._is_initialized:
            return ComponentStatus(status=HealthStatus.HEALTHY, message="MT5 connected")
        else:
            return ComponentStatus(status=HealthStatus.FAILED, message="MT5 not connected")

    def check_models(self) -> ComponentStatus:
        """Verify ML models are loaded."""
        if not self.model:
            return ComponentStatus(status=HealthStatus.FAILED, message="EnsembleModel not initialized")

        loaded = []
        if self.model._ppo_model:
            loaded.append("PPO")
        if self.model.lstm_model:
            loaded.append("LSTM")

        if not loaded:
            return ComponentStatus(status=HealthStatus.FAILED, message="No models loaded")

        return ComponentStatus(
            status=HealthStatus.HEALTHY,
            message=f"Models loaded: {', '.join(loaded)}",
            details={"loaded_models": loaded}
        )

    def check_config(self) -> ComponentStatus:
        """Validate critical configuration."""
        # Pydantic already validated most things on init.
        # Here we can check for sensitive placeholders or illogical combinations.
        if self.cfg.is_live and self.cfg.mt5_password == "password":
            return ComponentStatus(status=HealthStatus.FAILED, message="Production mode with default password!")

        return ComponentStatus(status=HealthStatus.HEALTHY, message="Configuration valid")

    def check_disk_space(self) -> ComponentStatus:
        """Check if log directory has enough space (min 100MB)."""
        logs_dir = self.cfg.logs_dir
        if not logs_dir.exists():
            try:
                logs_dir.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                return ComponentStatus(status=HealthStatus.FAILED, message=f"Cannot create logs dir: {e}")

        usage = shutil.disk_usage(logs_dir)
        free_mb = usage.free / (1024 * 1024)

        if free_mb < 100:
            return ComponentStatus(
                status=HealthStatus.FAILED,
                message=f"Low disk space: {free_mb:.2f}MB free",
                details={"free_mb": free_mb}
            )

        return ComponentStatus(
            status=HealthStatus.HEALTHY,
            message="Sufficient disk space",
            details={"free_mb": free_mb}
        )

    def get_full_report(self) -> HealthCheckResponse:
        """Aggregate all checks into a single report."""
        components = {
            "liveness": self.check_liveness(),
            "database": self.check_database(),
            "mt5": self.check_mt5(),
            "models": self.check_models(),
            "config": self.check_config(),
            "disk": self.check_disk_space(),
        }

        # Determine overall status
        if any(c.status == HealthStatus.FAILED for c in components.values()):
            overall_status = HealthStatus.FAILED
        elif any(c.status == HealthStatus.DEGRADED for c in components.values()):
            overall_status = HealthStatus.DEGRADED
        else:
            overall_status = HealthStatus.HEALTHY

        return HealthCheckResponse(
            status=overall_status,
            uptime_seconds=time.time() - self.start_time,
            components=components
        )

    def run_startup_gate(self) -> None:
        """
        Execute critical checks and abort startup if they fail.
        Used by main.py to prevent running in a broken state.
        """
        report = self.get_full_report()

        if report.status == HealthStatus.FAILED:
            logger.critical("Startup Health Gate FAILED!")
            for name, comp in report.components.items():
                if comp.status == HealthStatus.FAILED:
                    logger.error(f"  - {name}: {comp.message}")

            # In LIVE mode, any failure is fatal.
            # In DEMO mode, we might allow some failures (e.g. models if it's just testing connectivity)
            # but usually it's safer to just fail.
            sys.exit(1)

        logger.info("Startup Health Gate PASSED")

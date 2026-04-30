"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/core/health.py
Enterprise health monitoring and startup safety gates.
Author : triqbit
License: MIT
"""
from __future__ import annotations

import logging
import shutil
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional

from fastapi import FastAPI, Response
from pydantic import BaseModel, Field
from sqlalchemy import text

from src.core.config import TradingConfig
from src.core.config_validator import ConfigValidator
from src.core.trade_logger import TradeLogger
from src.models.ensemble import EnsembleModel
from src.trading.mt5_connector import MT5Connector

logger = logging.getLogger(__name__)


class HealthStatus(str, Enum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    FAILED = "FAILED"


class HealthResponse(BaseModel):
    """Typed health check response."""
    status: HealthStatus
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    version: str = "1.0.0"
    checks: Dict[str, Dict[str, Any]]


class HealthChecker:
    """
    Coordinates enterprise-grade health probes.
    Covers liveness, readiness, and deep dependency inspection.
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
        self.validator = ConfigValidator(config)

    def check_liveness(self) -> HealthResponse:
        """Is the application process alive?"""
        return HealthResponse(
            status=HealthStatus.HEALTHY,
            checks={"process": {"status": "running", "message": "Application is alive"}}
        )

    def check_readiness(self) -> HealthResponse:
        """Is the application ready to handle trading operations?"""
        checks = {}

        # 1. Config Check
        is_config_valid, config_errors = self.validator.validate()
        checks["config"] = {
            "status": "HEALTHY" if is_config_valid else "FAILED",
            "errors": config_errors
        }

        # 2. Database Check
        db_status = "FAILED"
        db_msg = "TradeLogger not initialized"
        if self.trade_logger:
            try:
                # Simple query to verify connection
                with self.trade_logger.Session() as session:
                    session.execute(text("SELECT 1"))
                db_status = "HEALTHY"
                db_msg = "Database connection verified"
            except Exception as e:
                db_msg = f"Database connection failed: {e!s}"
        checks["database"] = {"status": db_status, "message": db_msg}

        # 3. MT5 Check (if not in backtest mode)
        if self.cfg.mode != "backtest":
            mt5_status = "FAILED"
            mt5_msg = "MT5Connector not initialized"
            if self.connector:
                if self.connector._is_initialized:
                    mt5_status = "HEALTHY"
                    mt5_msg = "MT5 connection active"
                else:
                    mt5_msg = "MT5 connection inactive"
            checks["mt5"] = {"status": mt5_status, "message": mt5_msg}

        # 4. Model Check
        model_status = "FAILED"
        model_msg = "EnsembleModel not initialized"
        if self.model:
            # Check if at least one model is loaded
            models_loaded = []
            if self.model._ppo_model is not None:
                models_loaded.append("PPO")
            if self.model.lstm_model is not None:
                models_loaded.append("LSTM")

            if models_loaded:
                model_status = "HEALTHY" if len(models_loaded) >= 1 else "DEGRADED"
                model_msg = f"Models loaded: {', '.join(models_loaded)}"
            else:
                model_msg = "No models loaded in ensemble"
        checks["models"] = {"status": model_status, "message": model_msg}

        # 5. Disk Space Check
        disk_status = "HEALTHY"
        disk_msg = "Disk space sufficient"
        try:
            usage = shutil.disk_usage(self.cfg.logs_dir if self.cfg.logs_dir.exists() else ".")
            free_gb = usage.free / (1024**3)
            if free_gb < 1.0:
                disk_status = "DEGRADED"
                disk_msg = f"Low disk space: {free_gb:.2f} GB free"
            if free_gb < 0.1:
                disk_status = "FAILED"
                disk_msg = f"Critical disk space: {free_gb:.2f} GB free"
        except Exception as e:
            disk_status = "DEGRADED"
            disk_msg = f"Could not check disk space: {e!s}"
        checks["disk_space"] = {"status": disk_status, "message": disk_msg, "free_gb": f"{free_gb:.2f}" if 'free_gb' in locals() else "N/A"}

        # Overall Status
        all_statuses = [c["status"] for c in checks.values()]
        if "FAILED" in all_statuses:
            overall = HealthStatus.FAILED
        elif "DEGRADED" in all_statuses:
            overall = HealthStatus.DEGRADED
        else:
            overall = HealthStatus.HEALTHY

        return HealthResponse(status=overall, checks=checks)

    def run_startup_health_gate(self) -> None:
        """
        Hard health gate for application startup.
        Fails fast if critical dependencies are unreachable.
        """
        logger.info("Executing startup health gate...")
        health = self.check_readiness()

        if health.status == HealthStatus.FAILED:
            logger.critical("Startup health gate FAILED:")
            for name, result in health.checks.items():
                if result["status"] == "FAILED":
                    logger.critical("  - %s: %s", name, result.get("message") or result.get("errors"))
            import sys
            sys.exit(1)

        if health.status == HealthStatus.DEGRADED:
            logger.warning("Startup health gate DEGRADED. Proceeding with caution:")
            for name, result in health.checks.items():
                if result["status"] == "DEGRADED":
                    logger.warning("  - %s: %s", name, result.get("message"))

        logger.info("Startup health gate PASSED.")


def create_health_app(checker: HealthChecker) -> FastAPI:
    """Factory to create FastAPI application for health monitoring."""
    app = FastAPI(title="MT5 AI Trader Health Monitor")

    @app.get("/health/liveness", response_model=HealthResponse)
    def liveness():
        """Liveness probe - is the process alive?"""
        return checker.check_liveness()

    @app.get("/health/readiness", response_model=HealthResponse)
    def readiness(response: Response):
        """Readiness probe - are all dependencies reachable?"""
        health = checker.check_readiness()
        if health.status == HealthStatus.FAILED:
            response.status_code = 503
        return health

    return app

"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/core/health.py
Startup health checks and readiness probes.
Author : triqbit
License: MIT
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel
from sqlalchemy import create_engine, text

from src.core.config import TradingConfig
from src.trading.mt5_connector import MT5Connector

logger = logging.getLogger(__name__)

HealthStatus = Literal["healthy", "degraded", "failed"]


class HealthReport(BaseModel):
    """Structured health report for the system."""
    status: HealthStatus
    checks: Dict[str, bool]
    details: Dict[str, str]


class HealthChecker:
    """
    Performs system-wide readiness checks before startup.
    Ensures database, MT5, and models are available.
    """

    def __init__(
        self,
        config: TradingConfig,
        connector: MT5Connector,
        model_paths: Optional[List[Path]] = None,
    ) -> None:
        self.cfg = config
        self.connector = connector
        self.model_paths = model_paths or [config.model_path]

    def check_database(self) -> bool:
        """Verify database connectivity."""
        try:
            # Synchronize with main.py fallback logic
            db_url = (
                self.cfg.database_url
                if "sqlite" in self.cfg.database_url
                else "sqlite:///trades.db"
            )
            engine = create_engine(db_url)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.error("Health Check: Database connection failed: %s", e)
            return False

    def check_mt5(self) -> bool:
        """Verify MT5 terminal connectivity."""
        try:
            return self.connector.connect()
        except Exception as e:
            logger.error("Health Check: MT5 connection failed: %s", e)
            return False

    def check_model(self) -> bool:
        """Verify AI model existence."""
        for path in self.model_paths:
            if path.exists():
                return True
        logger.error("Health Check: No model files found in %s", self.model_paths)
        return False

    def check_logs(self) -> bool:
        """Verify log directory is writeable."""
        log_dir = self.cfg.logs_dir
        try:
            log_dir.mkdir(parents=True, exist_ok=True)
            test_file = log_dir / ".health_check"
            test_file.touch()
            test_file.unlink()
            return True
        except Exception as e:
            logger.error("Health Check: Log directory %s not writeable: %s", log_dir, e)
            return False

    def run_all(self) -> HealthReport:
        """Run all readiness checks and return a report."""
        checks = {
            "database": self.check_database(),
            "mt5": self.check_mt5(),
            "model": self.check_model(),
            "logs": self.check_logs(),
        }

        # Logic for overall status
        if all(checks.values()):
            status = "healthy"
        elif not checks["database"] or not checks["logs"]:
            # Hard failures: cannot log trades or write logs
            status = "failed"
        elif self.cfg.mode in ("demo", "live") and not checks["mt5"]:
            # MT5 connection is CRITICAL for live/demo
            status = "failed"
        else:
            # e.g. missing model or MT5 in backtest mode
            status = "degraded"

        details = {
            "database": "Connected" if checks["database"] else "Connection Failed",
            "mt5": "Connected" if checks["mt5"] else "Connection Failed",
            "model": "Found" if checks["model"] else "Missing",
            "logs": "Writeable" if checks["logs"] else "Permission Denied",
        }

        return HealthReport(status=status, checks=checks, details=details)

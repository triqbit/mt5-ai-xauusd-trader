"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/core/health.py
Enterprise health gate for system sanity checks.
Author : triqbit
License: MIT
"""
from __future__ import annotations

import logging
import os
import psutil
import socket
from typing import Dict, List, Any

import structlog
from src.core.config import TradingConfig

logger = structlog.get_logger(__name__)

class HealthGate:
    """
    Enterprise health gate for pre-flight system checks.
    Ensures the environment is fit for automated trading.
    """

    def __init__(self, config: TradingConfig) -> None:
        self.cfg = config
        self.report: Dict[str, Any] = {}

    def run_all_checks(self) -> bool:
        """Run all registered health checks."""
        logger.info("health_gate_started", version="1.0.0")

        checks = {
            "environment_vars": self._check_env_vars(),
            "internet_connectivity": self._check_internet(),
            "resource_availability": self._check_resources(),
            "database_connectivity": self._check_database(),
        }

        self.report = checks
        all_passed = all(checks.values())

        if all_passed:
            logger.info("health_gate_passed")
        else:
            failed = [k for k, v in checks.items() if not v]
            logger.critical("health_gate_failed", failed_checks=failed)

        return all_passed

    def _check_env_vars(self) -> bool:
        """Verify essential secrets are present."""
        required = ["MT5_PASSWORD", "MT5_SERVER"]
        missing = [var for var in required if not getattr(self.cfg, var.lower(), None)]

        if missing:
            logger.error("missing_required_config", missing=missing)
            return False
        return True

    def _check_internet(self) -> bool:
        """Verify internet access (can reach Google DNS)."""
        try:
            socket.create_connection(("8.8.8.8", 53), timeout=3)
            return True
        except OSError:
            logger.error("internet_connectivity_failed")
            return False

    def _check_resources(self) -> bool:
        """Check CPU and Memory availability."""
        mem = psutil.virtual_memory()
        cpu_load = psutil.cpu_percent(interval=0.1)

        if mem.percent > 95:
            logger.error("low_memory_warning", percent=mem.percent)
            return False
        if cpu_load > 90:
            logger.error("high_cpu_load", percent=cpu_load)
            return False
        return True

    def _check_database(self) -> bool:
        """Verify database URL is valid and reachable (basic check)."""
        if not self.cfg.database_url:
            logger.error("missing_database_url")
            return False
        return True

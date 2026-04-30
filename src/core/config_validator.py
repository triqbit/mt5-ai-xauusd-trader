"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/core/config_validator.py
Comprehensive startup validation for TradingConfig.
Author : triqbit
License: MIT
"""
from __future__ import annotations

import logging
import os
from typing import List, Tuple

from src.core.config import TradingConfig

logger = logging.getLogger(__name__)


class ConfigValidator:
    """
    Performs enterprise-grade validation of the application configuration.
    Ensures that the bot does not start with insecure or invalid parameters.
    """

    def __init__(self, config: TradingConfig) -> None:
        self.cfg = config

    def validate(self) -> Tuple[bool, List[str]]:
        """
        Runs all validation checks.
        Returns:
            Tuple of (is_valid: bool, errors: List[str])
        """
        errors = []

        # 1. MT5 Credential Formatting & Placeholder Detection
        if self.cfg.mt5_login <= 0:
            errors.append("MT5_LOGIN must be a positive integer.")

        placeholders = ["password", "your_password", "SECRET", "123456"]
        if not self.cfg.mt5_password or any(p in self.cfg.mt5_password.lower() for p in placeholders):
            errors.append("MT5_PASSWORD is missing or appears to be a placeholder.")

        if not self.cfg.mt5_server or self.cfg.mt5_server in ["server", "broker_server"]:
            errors.append("MT5_SERVER is missing or set to a default placeholder.")

        # 2. Mandatory LIVE Mode Confirmation
        if self.cfg.is_live:
            confirm = os.getenv("CONFIRM_LIVE_TRADING", "NO")
            if confirm != "YES":
                errors.append("LIVE trading mode requires explicit confirmation via CONFIRM_LIVE_TRADING='YES' env var.")

        # 3. Risk Limit Alignment (Enterprise Standards)
        if self.cfg.risk_per_trade > 0.01:
            errors.append(f"risk_per_trade ({self.cfg.risk_per_trade}) exceeds enterprise safety limit of 0.01.")

        if self.cfg.max_daily_loss > 0.05:
            errors.append(f"max_daily_loss ({self.cfg.max_daily_loss}) exceeds enterprise safety limit of 0.05.")

        # 4. Model Configuration
        if not self.cfg.model_path.exists() and self.cfg.mode != "backtest":
            # We only warn here unless it's a hard requirement for the specific algo
            logger.warning("Model path %s does not exist. Application may fail during inference.", self.cfg.model_path)

        # 5. Database URL Check
        if "postgresql" in self.cfg.database_url and "password" in self.cfg.database_url:
            if "@localhost" in self.cfg.database_url:
                logger.warning("Using PostgreSQL on localhost with default 'password'. Not recommended for production.")

        is_valid = len(errors) == 0
        return is_valid, errors

    def validate_and_exit(self) -> None:
        """
        Validates configuration and exits the application if critical errors are found.
        """
        is_valid, errors = self.validate()
        if not is_valid:
            logger.critical("Configuration validation FAILED:")
            for error in errors:
                logger.critical("  - %s", error)
            import sys
            sys.exit(1)
        logger.info("Configuration validation PASSED.")

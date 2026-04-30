"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/core/config_validator.py
Validates configuration at startup to prevent unsafe or misconfigured execution.
Author : triqbit
License: MIT
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum
from typing import List

from src.core.config import TradingConfig


class ValidationLevel(Enum):
    ERROR = "ERROR"
    WARNING = "WARNING"


@dataclass
class ValidationIssue:
    field: str
    level: ValidationLevel
    message: str


@dataclass
class ValidationResult:
    issues: List[ValidationIssue] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return not any(issue.level == ValidationLevel.ERROR for issue in self.issues)


class ConfigValidator:
    """Validator for TradingConfig to ensure production safety and correctness."""

    PLACEHOLDERS = {"password", "CHANGE_ME", "your_password", "test", "default", "your_token"}

    def validate(self, config: TradingConfig) -> ValidationResult:
        result = ValidationResult()

        # 1. MT5 Credentials
        if config.mt5_login <= 0:
            result.issues.append(
                ValidationIssue("mt5_login", ValidationLevel.ERROR, "MT5 login must be a positive integer.")
            )

        if not config.mt5_password or config.mt5_password in self.PLACEHOLDERS:
            result.issues.append(
                ValidationIssue("mt5_password", ValidationLevel.ERROR, "MT5 password is empty or using a placeholder.")
            )

        if not config.mt5_server:
            result.issues.append(
                ValidationIssue("mt5_server", ValidationLevel.ERROR, "MT5 server must be specified.")
            )

        # 2. Mode-Specific Validation
        if config.mode == "live":
            # Explicit confirmation for LIVE mode
            if os.getenv("CONFIRM_LIVE_TRADING") != "YES":
                result.issues.append(
                    ValidationIssue(
                        "mode",
                        ValidationLevel.ERROR,
                        "LIVE mode requires CONFIRM_LIVE_TRADING='YES' environment variable."
                    )
                )

            # Prevent using demo servers in LIVE mode
            if "demo" in config.mt5_server.lower():
                result.issues.append(
                    ValidationIssue(
                        "mt5_server",
                        ValidationLevel.ERROR,
                        "Cannot use a 'demo' server in LIVE mode."
                    )
                )

            # Localhost warnings for production
            if "localhost" in config.database_url or "127.0.0.1" in config.database_url:
                result.issues.append(
                    ValidationIssue(
                        "database_url",
                        ValidationLevel.WARNING,
                        "Using localhost database in LIVE mode is discouraged."
                    )
                )

            if "localhost" in config.redis_url or "127.0.0.1" in config.redis_url:
                result.issues.append(
                    ValidationIssue(
                        "redis_url",
                        ValidationLevel.WARNING,
                        "Using localhost redis in LIVE mode is discouraged."
                    )
                )

        # 3. Risk Parameters (referencing RISK_LIMITS.md)
        if config.risk_per_trade > 0.01:
             result.issues.append(
                ValidationIssue(
                    "risk_per_trade",
                    ValidationLevel.ERROR,
                    "risk_per_trade > 1% exceeds hard limits in RISK_LIMITS.md."
                )
            )

        if config.max_daily_loss > 0.05:
            result.issues.append(
                ValidationIssue(
                    "max_daily_loss",
                    ValidationLevel.ERROR,
                    "max_daily_loss > 5% exceeds hard limits in RISK_LIMITS.md."
                )
            )
        elif config.max_daily_loss < config.risk_per_trade:
             result.issues.append(
                ValidationIssue(
                    "max_daily_loss",
                    ValidationLevel.ERROR,
                    "max_daily_loss cannot be less than risk_per_trade."
                )
            )
        elif config.max_daily_loss < 2 * config.risk_per_trade:
            result.issues.append(
                ValidationIssue(
                    "max_daily_loss",
                    ValidationLevel.WARNING,
                    "max_daily_loss is tight (less than 2x risk_per_trade)."
                )
            )

        # 4. Monitoring
        if config.telegram_token and not config.telegram_chat_id:
             result.issues.append(
                ValidationIssue(
                    "telegram_chat_id",
                    ValidationLevel.WARNING,
                    "Telegram token provided but chat_id is missing."
                )
            )

        # 5. Placeholder secrets
        for field_name in ["metaapi_token", "telegram_token"]:
            val = getattr(config, field_name, "")
            if val in self.PLACEHOLDERS:
                result.issues.append(
                    ValidationIssue(
                        field_name,
                        ValidationLevel.ERROR,
                        f"{field_name} is using a placeholder value."
                    )
                )

        return result

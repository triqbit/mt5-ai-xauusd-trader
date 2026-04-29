"""
Startup configuration validation layer for MT5 AI/ML Trading Bot.
Ensures production safety and prevents misconfigured launches.
"""
from __future__ import annotations

import os
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field

from src.core.config import TradingConfig


class ValidationSeverity(str, Enum):
    CRITICAL = "CRITICAL"  # Must block startup
    WARNING = "WARNING"    # Degraded state, allow startup


class ValidationIssue(BaseModel):
    field: str
    message: str
    severity: ValidationSeverity
    value: Optional[str] = None


class ValidationResult(BaseModel):
    is_valid: bool
    issues: List[ValidationIssue] = Field(default_factory=list)

    @property
    def has_critical(self) -> bool:
        return any(issue.severity == ValidationSeverity.CRITICAL for issue in self.issues)


def validate_config(cfg: TradingConfig) -> ValidationResult:
    """
    Performs comprehensive validation of the trading configuration.
    Returns a ValidationResult containing any detected issues.
    """
    issues: List[ValidationIssue] = []

    # 1. MT5 Credentials
    if cfg.mt5_login <= 0:
        issues.append(
            ValidationIssue(
                field="mt5_login",
                message="MT5 login must be a positive integer.",
                severity=ValidationSeverity.CRITICAL,
                value=str(cfg.mt5_login),
            )
        )

    if not cfg.mt5_password or cfg.mt5_password in ("password", "your_password", "CHANGE_ME"):
        issues.append(
            ValidationIssue(
                field="mt5_password",
                message="MT5 password is missing or using a placeholder value.",
                severity=ValidationSeverity.CRITICAL,
            )
        )

    if not cfg.mt5_server or cfg.mt5_server in ("server_name", "Broker-Server"):
        issues.append(
            ValidationIssue(
                field="mt5_server",
                message="MT5 server is missing or using a placeholder value.",
                severity=ValidationSeverity.CRITICAL,
                value=cfg.mt5_server,
            )
        )

    # 2. Secret Placeholders
    placeholders = ["your_token_here", "INSERT_TOKEN", "CHANGE_ME", "password"]

    if cfg.telegram_token in placeholders:
        issues.append(
            ValidationIssue(
                field="telegram_token",
                message="Telegram token is using a placeholder value.",
                severity=ValidationSeverity.WARNING,
                value=cfg.telegram_token,
            )
        )

    if "password" in cfg.database_url and cfg.mode == "live":
        issues.append(
            ValidationIssue(
                field="database_url",
                message="Production mode detected using default database password.",
                severity=ValidationSeverity.CRITICAL,
            )
        )

    # 3. LIVE Mode Restrictions
    if cfg.mode == "live":
        confirm_live = os.getenv("CONFIRM_LIVE_TRADING", "NO").upper()
        if confirm_live != "YES":
            issues.append(
                ValidationIssue(
                    field="mode",
                    message="LIVE mode requires explicit confirmation via CONFIRM_LIVE_TRADING='YES' environment variable.",
                    severity=ValidationSeverity.CRITICAL,
                    value=cfg.mode,
                )
            )

        # Stricter risk in LIVE
        if cfg.risk_per_trade > 0.015:
            issues.append(
                ValidationIssue(
                    field="risk_per_trade",
                    message="Risk per trade > 1.5% is restricted in LIVE mode.",
                    severity=ValidationSeverity.CRITICAL,
                    value=str(cfg.risk_per_trade),
                )
            )

    # 4. Risk parameter safety (Generic)
    if cfg.max_daily_loss > 0.15:
        issues.append(
            ValidationIssue(
                field="max_daily_loss",
                message="Max daily loss > 15% is considered unsafe.",
                severity=ValidationSeverity.WARNING,
                value=str(cfg.max_daily_loss),
            )
        )

    return ValidationResult(
        is_valid=not any(i.severity == ValidationSeverity.CRITICAL for i in issues),
        issues=issues
    )

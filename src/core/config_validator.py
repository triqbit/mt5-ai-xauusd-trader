"""
MT5 AI/ML Trading Bot - Startup Configuration Validator
src/core/config_validator.py
"""
from __future__ import annotations

from typing import List, Literal

from pydantic import BaseModel, Field

from src.core.config import TradingConfig


class ValidationIssue(BaseModel):
    """Represents a single configuration validation issue."""
    field: str
    level: Literal["ERROR", "WARNING"]
    message: str


class ValidationResult(BaseModel):
    """Container for all validation issues found during startup."""
    is_valid: bool
    issues: List[ValidationIssue] = Field(default_factory=list)

    @property
    def errors(self) -> List[ValidationIssue]:
        return [i for i in self.issues if i.level == "ERROR"]

    @property
    def warnings(self) -> List[ValidationIssue]:
        return [i for i in self.issues if i.level == "WARNING"]


class ConfigValidator:
    """Enterprise-grade configuration validator."""

    PLACEHOLDERS = {
        "password", "test", "token", "your_token", "your_password",
        "your_server", "change_me", "placeholder", "default"
    }

    @classmethod
    def validate(cls, cfg: TradingConfig) -> ValidationResult:
        """Perform comprehensive validation of the trading configuration."""
        issues: List[ValidationIssue] = []

        # 1. MT5 Credentials
        if cfg.mt5_login <= 0:
            issues.append(ValidationIssue(
                field="mt5_login",
                level="ERROR",
                message="MT5 Login must be a positive integer."
            ))

        if any(p in cfg.mt5_password.lower() for p in cls.PLACEHOLDERS):
            issues.append(ValidationIssue(
                field="mt5_password",
                level="ERROR",
                message="MT5 Password appears to be using a default or placeholder value."
            ))

        if any(p in cfg.mt5_server.lower() for p in cls.PLACEHOLDERS):
            issues.append(ValidationIssue(
                field="mt5_server",
                level="ERROR",
                message="MT5 Server appears to be using a default or placeholder value."
            ))

        # 2. Trading Mode Restrictions
        if cfg.mode == "live":
            if not cfg.confirm_live_trading:
                issues.append(ValidationIssue(
                    field="confirm_live_trading",
                    level="ERROR",
                    message="LIVE mode requires explicit confirmation. Set CONFIRM_LIVE_TRADING=true."
                ))

            # Incompatible environment variable combinations
            if "demo" in cfg.mt5_server.lower():
                issues.append(ValidationIssue(
                    field="mt5_server",
                    level="ERROR",
                    message="Trading mode is LIVE but MT5 server appears to be a DEMO server."
                ))

        # 3. Risk Parameters
        if cfg.risk_per_trade > 0.02:
            # Note: Pydantic also validates this, but we reinforce it here
            issues.append(ValidationIssue(
                field="risk_per_trade",
                level="ERROR",
                message="Risk per trade exceeds maximum production safety limit of 2%."
            ))

        if cfg.max_daily_loss > 0.10:
            issues.append(ValidationIssue(
                field="max_daily_loss",
                level="WARNING",
                message="Max daily loss is set above 10%, which is high for production."
            ))

        if cfg.max_positions > 5:
             issues.append(ValidationIssue(
                field="max_positions",
                level="WARNING",
                message="Max positions > 5 increases systemic risk."
            ))

        # 4. Secrets placeholders
        if cfg.telegram_token and any(p in cfg.telegram_token.lower() for p in cls.PLACEHOLDERS):
            issues.append(ValidationIssue(
                field="telegram_token",
                level="WARNING",
                message="Telegram token appears to be a placeholder."
            ))

        if "password" in cfg.database_url and "postgresql://trader:password" in cfg.database_url:
             issues.append(ValidationIssue(
                field="database_url",
                level="ERROR",
                message="Database URL is using default credentials."
            ))

        # Determine if overall result is valid (no ERRORs)
        is_valid = not any(i.level == "ERROR" for i in issues)

        return ValidationResult(is_valid=is_valid, issues=issues)

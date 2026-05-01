"""
Startup Validation Layer for MT5 AI Trading Bot.
src/core/config_validator.py
"""

import os
from typing import List, NamedTuple

from src.core.config import TradingConfig


class ValidationError(NamedTuple):
    field: str
    message: str
    critical: bool

class ValidationResult(NamedTuple):
    success: bool
    errors: List[ValidationError]

class ConfigValidator:
    """Validates configuration at startup to prevent unsafe operations."""

    def __init__(self, config: TradingConfig):
        self.config = config
        self.errors: List[ValidationError] = []

    def validate(self) -> ValidationResult:
        """Runs all validation rules and returns a result."""
        self.errors = []

        self._check_mt5_credentials()
        self._check_live_mode_confirmation()
        self._check_placeholder_secrets()
        self._check_risk_parameters()
        self._check_incompatible_settings()

        # Application is valid only if there are no critical errors
        success = not any(e.critical for e in self.errors)
        return ValidationResult(success=success, errors=self.errors)

    def _check_mt5_credentials(self) -> None:
        """Verify MT5 credentials are provided and formatted correctly."""
        if self.config.mt5_login <= 0:
            self.errors.append(ValidationError("MT5_LOGIN", "MT5 login must be a positive integer.", True))

        if not self.config.mt5_server or self.config.mt5_server.lower() in ["", "server_name", "test"]:
            self.errors.append(ValidationError("MT5_SERVER", "MT5 server name is missing or using placeholder.", True))

        if not self.config.mt5_password or self.config.mt5_password.lower() in ["", "password", "test"]:
            self.errors.append(ValidationError("MT5_PASSWORD", "MT5 password is missing or using placeholder.", True))

    def _check_live_mode_confirmation(self) -> None:
        """Enforce explicit confirmation for LIVE trading."""
        if self.config.mode == "live":
            confirm = os.getenv("CONFIRM_LIVE_TRADING", "").upper()
            if confirm != "YES":
                self.errors.append(ValidationError(
                    "MODE",
                    "LIVE mode detected but CONFIRM_LIVE_TRADING is not set to 'YES'.",
                    True
                ))

    def _check_placeholder_secrets(self) -> None:
        """Detect default or placeholder values in secrets."""
        # Check database URL
        default_db = "postgresql://trader:password@localhost:5432/mt5_trades"
        if self.config.database_url == default_db:
             self.errors.append(ValidationError(
                 "DATABASE_URL",
                 "Database URL is using default placeholder credentials.",
                 True
             ))

        # Check Telegram
        if self.config.telegram_token and "YOUR_TOKEN" in self.config.telegram_token.upper():
            self.errors.append(ValidationError("TELEGRAM_TOKEN", "Telegram token contains placeholder text.", True))

    def _check_risk_parameters(self) -> None:
        """Verify risk parameters are within safe enterprise bounds."""
        # secondary check as pydantic also handles this
        if self.config.risk_per_trade > 0.02:
            self.errors.append(ValidationError("RISK_PER_TRADE", "Risk per trade > 2% is strictly prohibited.", True))

        if self.config.max_daily_loss > 0.15:
            self.errors.append(ValidationError("MAX_DAILY_LOSS", "Max daily loss > 15% is outside safe range.", True))

    def _check_incompatible_settings(self) -> None:
        """Detect incompatible configuration combinations."""
        # Example: LIVE mode with very high max positions
        if self.config.mode == "live" and self.config.max_positions > 5:
            self.errors.append(ValidationError(
                "MAX_POSITIONS",
                "Maximum positions > 5 is not allowed in LIVE mode for safety.",
                True
            ))

        # Backtest mode doesn't need Telegram
        if self.config.mode == "backtest" and self.config.telegram_token:
             self.errors.append(ValidationError(
                 "TELEGRAM_TOKEN",
                 "Telegram notifications should be disabled in backtest mode.",
                 False # Non-critical warning
             ))

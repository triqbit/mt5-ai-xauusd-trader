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
            self.errors.append(
                ValidationError("MT5_LOGIN", "MT5 login must be a positive integer.", True)
            )

        placeholders = ["", "server_name", "test", "your_server_here"]
        if not self.config.mt5_server or self.config.mt5_server.lower() in placeholders:
            self.errors.append(
                ValidationError(
                    "MT5_SERVER", "MT5 server name is missing or using placeholder.", True
                )
            )

        password_placeholders = ["", "password", "test", "your_password_here"]
        mt5_password = self.config.mt5_password.get_secret_value()
        if not mt5_password or mt5_password.lower() in password_placeholders:
            self.errors.append(
                ValidationError(
                    "MT5_PASSWORD", "MT5 password is missing or using placeholder.", True
                )
            )

    def _check_live_mode_confirmation(self) -> None:
        """Enforce explicit confirmation for LIVE trading."""
        if self.config.mode == "live":
            confirm = os.getenv("CONFIRM_LIVE_TRADING", "").upper()
            if confirm != "YES":
                self.errors.append(
                    ValidationError(
                        "MODE",
                        "LIVE mode detected but CONFIRM_LIVE_TRADING is not set to 'YES'.",
                        True,
                    )
                )

    def _check_placeholder_secrets(self) -> None:
        """Detect default or placeholder values in secrets."""
        # Check database URL
        default_db = "postgresql://trader:password@localhost:5432/mt5_trades"
        if self.config.database_url.get_secret_value() == default_db:
            self.errors.append(
                ValidationError(
                    "DATABASE_URL", "Database URL is using default placeholder credentials.", True
                )
            )

        # Check Telegram
        telegram_token = self.config.telegram_token.get_secret_value()
        if telegram_token and any(p in telegram_token.upper() for p in ["YOUR_TOKEN", "CHANGE_ME"]):
            self.errors.append(
                ValidationError("TELEGRAM_TOKEN", "Telegram token contains placeholder text.", True)
            )

        # Check MetaAPI
        metaapi_token = self.config.metaapi_token.get_secret_value()
        if metaapi_token and any(p in metaapi_token.upper() for p in ["YOUR_TOKEN", "CHANGE_ME"]):
            self.errors.append(
                ValidationError("METAAPI_TOKEN", "MetaAPI token contains placeholder text.", True)
            )

        if self.config.metaapi_account_id and any(
            p in self.config.metaapi_account_id.upper() for p in ["YOUR_ACCOUNT_ID", "CHANGE_ME"]
        ):
            self.errors.append(
                ValidationError(
                    "METAAPI_ACCOUNT_ID", "MetaAPI account ID contains placeholder text.", True
                )
            )

    def _check_risk_parameters(self) -> None:
        """Verify risk parameters are within safe enterprise bounds."""
        # 1. Per-trade risk limits (RISK_LIMITS.md 1.3)
        if self.config.risk_per_trade > 0.02:
            self.errors.append(
                ValidationError(
                    "RISK_PER_TRADE",
                    "Risk per trade > 2% is strictly prohibited (Enterprise Limit: 1%).",
                    True,
                )
            )

        # 2. Daily loss limits (RISK_LIMITS.md 2.1)
        if self.config.max_daily_loss > 0.15:
            self.errors.append(
                ValidationError(
                    "MAX_DAILY_LOSS",
                    "Max daily loss > 15% is outside safe range (Emergency Stop: 5%).",
                    True,
                )
            )

        # 3. Position limits (RISK_LIMITS.md 1.1)
        if self.config.max_positions > 10:
            self.errors.append(
                ValidationError(
                    "MAX_POSITIONS",
                    "Maximum positions > 10 is strictly prohibited for capital safety.",
                    True,
                )
            )

    def _check_incompatible_settings(self) -> None:
        """Detect incompatible configuration combinations."""
        # 1. LIVE mode restrictions
        if self.config.mode == "live" and self.config.max_positions > 5:
            self.errors.append(
                ValidationError(
                    "MAX_POSITIONS",
                    "Maximum positions > 5 is not allowed in LIVE mode for safety.",
                    True,
                )
            )

        # 2. MetaAPI Consistency
        if self.config.metaapi_token and not self.config.metaapi_account_id:
            self.errors.append(
                ValidationError(
                    "METAAPI_ACCOUNT_ID",
                    "MetaAPI account ID is required when MetaAPI token is provided.",
                    True,
                )
            )

        if self.config.metaapi_account_id and not self.config.metaapi_token:
            self.errors.append(
                ValidationError(
                    "METAAPI_TOKEN",
                    "MetaAPI token is required when MetaAPI account ID is provided.",
                    True,
                )
            )

        # 3. Telegram Consistency
        if self.config.telegram_token and not self.config.telegram_chat_id:
            self.errors.append(
                ValidationError(
                    "TELEGRAM_CHAT_ID",
                    "Telegram chat ID is required when Telegram token is provided.",
                    True,
                )
            )

        if self.config.telegram_chat_id and not self.config.telegram_token:
            self.errors.append(
                ValidationError(
                    "TELEGRAM_TOKEN",
                    "Telegram token is required when Telegram chat ID is provided.",
                    True,
                )
            )

        # 4. Mode-specific warnings
        if self.config.mode == "backtest" and self.config.telegram_token:
            self.errors.append(
                ValidationError(
                    "TELEGRAM_TOKEN",
                    "Telegram notifications should be disabled in backtest mode.",
                    False,  # Non-critical warning
                )
            )

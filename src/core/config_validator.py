"""
Startup Validation Layer for MT5 AI Trading Bot.
src/core/config_validator.py
"""

import sys
from pathlib import Path
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
        self._check_model_settings()
        self._check_risk_parameters()
        self._check_incompatible_settings()

        # Application is valid only if there are no critical errors
        success = not any(e.critical for e in self.errors)
        return ValidationResult(success=success, errors=self.errors)

    def _check_mt5_credentials(self) -> None:
        """Verify MT5 credentials are provided and formatted correctly."""
        if self.config.mt5_login <= 0:
            self.errors.append(
                ValidationError(
                    "MT5_LOGIN",
                    "MT5 login must be a positive integer. Check your .env file.",
                    True,
                )
            )

        mt5_placeholders = ["", "server_name", "test", "your_server_here", "change_me"]
        if not self.config.mt5_server or self.config.mt5_server.lower() in mt5_placeholders:
            self.errors.append(
                ValidationError(
                    "MT5_SERVER",
                    "MT5 server name is missing or using placeholder. Provide your broker's server name.",
                    True,
                )
            )

        password_placeholders = ["", "password", "test", "your_password_here", "change_me"]
        mt5_password = self.config.mt5_password.get_secret_value()
        if not mt5_password or mt5_password.lower() in password_placeholders:
            self.errors.append(
                ValidationError(
                    "MT5_PASSWORD",
                    "MT5 password is missing or using placeholder. Ensure your MT5 password is set.",
                    True,
                )
            )

        # Path validation for Windows
        if sys.platform == "win32":
            mt5_path = Path(self.config.mt5_path)
            if not mt5_path.exists():
                self.errors.append(
                    ValidationError(
                        "MT5_PATH",
                        f"MT5 terminal not found at: {mt5_path}. Verify MT5_PATH in .env.",
                        True,
                    )
                )

    def _check_live_mode_confirmation(self) -> None:
        """Enforce explicit confirmation for LIVE trading."""
        if self.config.mode == "live" and self.config.confirm_live_trading.upper() != "YES":
            self.errors.append(
                ValidationError(
                    "MODE",
                    "LIVE mode detected but CONFIRM_LIVE_TRADING is not set to 'YES'. "
                    "Safety gate: set CONFIRM_LIVE_TRADING=YES in your environment.",
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
                    "DATABASE_URL",
                    "Database URL is using default placeholder credentials. Update DATABASE_URL with a secure password.",
                    True,
                )
            )

        # Common placeholder patterns
        placeholders = ["YOUR_TOKEN", "CHANGE_ME", "YOUR_ACCOUNT_ID", "YOUR_CHAT_ID", "123456789"]

        # Check Telegram
        telegram_token = self.config.telegram_token.get_secret_value()
        if telegram_token and any(p in telegram_token.upper() for p in placeholders):
            self.errors.append(
                ValidationError(
                    "TELEGRAM_TOKEN",
                    "Telegram token contains placeholder text. Replace with your actual bot token.",
                    True,
                )
            )

        if self.config.telegram_chat_id and any(
            p in str(self.config.telegram_chat_id).upper() for p in placeholders
        ):
            self.errors.append(
                ValidationError(
                    "TELEGRAM_CHAT_ID",
                    "Telegram chat ID contains placeholder text. Replace with your actual chat ID.",
                    True,
                )
            )

        # Check MetaAPI
        metaapi_token = self.config.metaapi_token.get_secret_value()
        if metaapi_token and any(p in metaapi_token.upper() for p in placeholders):
            self.errors.append(
                ValidationError(
                    "METAAPI_TOKEN",
                    "MetaAPI token contains placeholder text. Replace with your actual MetaAPI token.",
                    True,
                )
            )

        if self.config.metaapi_account_id and any(
            p in self.config.metaapi_account_id.upper() for p in placeholders
        ):
            self.errors.append(
                ValidationError(
                    "METAAPI_ACCOUNT_ID",
                    "MetaAPI account ID contains placeholder text. Replace with your actual MetaAPI account ID.",
                    True,
                )
            )

    def _check_model_settings(self) -> None:
        """Verify model settings and path existence."""
        if self.config.mode != "backtest" and (
            not self.config.model_path.exists() or not self.config.model_path.is_file()
        ):
            self.errors.append(
                ValidationError(
                    "MODEL_PATH",
                    f"Model file not found at: {self.config.model_path}. "
                    "Ensure the model is trained and path is correct.",
                    True,
                )
            )

    def _check_risk_parameters(self) -> None:
        """Verify risk parameters are within safe enterprise bounds (RISK_LIMITS.md)."""
        # 1. Per-trade risk limits (RISK_LIMITS.md 1.3)
        # Policy limit is 1%, 2% is hard prohibition.
        if self.config.risk_per_trade > 0.02:
            self.errors.append(
                ValidationError(
                    "RISK_PER_TRADE",
                    f"Risk per trade {self.config.risk_per_trade*100}% exceeds the absolute maximum of 2%.",
                    True,
                )
            )
        elif self.config.risk_per_trade > 0.01:
            self.errors.append(
                ValidationError(
                    "RISK_PER_TRADE",
                    f"Risk per trade {self.config.risk_per_trade*100}% exceeds the policy limit of 1%.",
                    False,  # Non-critical warning
                )
            )

        # 2. Daily loss limits (RISK_LIMITS.md 2.1)
        # Level 4 (Emergency Stop) is 5%.
        if self.config.max_daily_loss > 0.06:
            self.errors.append(
                ValidationError(
                    "MAX_DAILY_LOSS",
                    f"Max daily loss {self.config.max_daily_loss*100}% exceeds hard stop of 6%.",
                    True,
                )
            )
        elif self.config.max_daily_loss > 0.05:
            self.errors.append(
                ValidationError(
                    "MAX_DAILY_LOSS",
                    f"Max daily loss {self.config.max_daily_loss*100}% exceeds emergency stop limit of 5%.",
                    False,
                )
            )

        # 3. Confidence Threshold (RISK_LIMITS.md 4.1)
        if self.config.confidence_threshold < 0.50:
            self.errors.append(
                ValidationError(
                    "CONFIDENCE_THRESHOLD",
                    f"Confidence threshold {self.config.confidence_threshold} is dangerously low (Min: 0.50).",
                    True,
                )
            )
        elif self.config.confidence_threshold < 0.55:
            self.errors.append(
                ValidationError(
                    "CONFIDENCE_THRESHOLD",
                    f"Confidence threshold {self.config.confidence_threshold} is below the recommended 0.55.",
                    False,
                )
            )

        # 4. Position limits (RISK_LIMITS.md 1.1)
        # Maximum 5 open positions is the policy limit.
        if self.config.max_positions > 10:
            self.errors.append(
                ValidationError(
                    "MAX_POSITIONS",
                    f"Maximum positions {self.config.max_positions} is strictly prohibited (Limit: 5).",
                    True,
                )
            )
        elif self.config.max_positions > 5:
            self.errors.append(
                ValidationError(
                    "MAX_POSITIONS",
                    f"Maximum positions {self.config.max_positions} exceeds the standard policy limit of 5.",
                    False,
                )
            )

        # 5. Circuit Breaker and R:R
        if self.config.circuit_breaker_threshold > 0.20:
             self.errors.append(
                ValidationError(
                    "CIRCUIT_BREAKER_THRESHOLD",
                    f"Circuit breaker {self.config.circuit_breaker_threshold*100}% is too high (Max: 20%).",
                    True,
                )
            )

        if self.config.min_risk_reward < 1.0:
            self.errors.append(
                ValidationError(
                    "MIN_RISK_REWARD",
                    f"Minimum R:R {self.config.min_risk_reward} must be at least 1.0.",
                    True,
                )
            )

        # 6. Consecutive Loss Limit
        if self.config.consecutive_loss_limit > 5:
             self.errors.append(
                ValidationError(
                    "CONSECUTIVE_LOSS_LIMIT",
                    f"Consecutive loss limit {self.config.consecutive_loss_limit} exceeds standard limit of 5.",
                    False,
                )
            )

    def _check_incompatible_settings(self) -> None:
        """Detect incompatible configuration combinations."""
        # 1. LIVE mode restrictions
        if self.config.mode == "live" and self.config.log_level == "DEBUG":
            self.errors.append(
                ValidationError(
                    "LOG_LEVEL",
                    "DEBUG logging in LIVE mode can cause performance degradation and log flooding.",
                    False,
                )
            )

        if self.config.mode == "live" and self.config.max_positions > 5:
            self.errors.append(
                ValidationError(
                    "MAX_POSITIONS",
                    "Maximum positions > 5 is strictly prohibited in LIVE mode for capital safety.",
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
                    "Telegram notifications should be disabled in backtest mode to avoid spam.",
                    False,
                )
            )

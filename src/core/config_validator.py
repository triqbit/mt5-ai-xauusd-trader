"""
Startup Validation Layer for MT5 AI Trading Bot.
src/core/config_validator.py
"""

import sys
from pathlib import Path
from typing import NamedTuple

from src.core.config import TradingConfig


class ValidationError(NamedTuple):
    field: str
    message: str
    critical: bool
    remedy: str = "N/A"


class ValidationResult(NamedTuple):
    success: bool
    errors: list[ValidationError]


class ConfigValidator:
    """Validates configuration at startup to prevent unsafe operations."""

    def __init__(self, config: TradingConfig):
        self.config = config
        self.errors: list[ValidationError] = []

    def validate(self) -> ValidationResult:
        """Runs all validation rules and returns a result."""
        self.errors = []

        self._check_mt5_credentials()
        self._check_market_settings()
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
        # Specific placeholders that shouldn't be used
        full_match_placeholders = ["TEST", "PASSWORD", "CHANGE_ME", "SERVER_NAME", ""]
        substring_placeholders = ["YOUR_SERVER_HERE", "YOUR_PASSWORD_HERE", "YOUR_TOKEN"]

        if self.config.mt5_login <= 0:
            self.errors.append(
                ValidationError(
                    "MT5_LOGIN",
                    "MT5 login must be a positive integer.",
                    True,
                    "Set MT5_LOGIN in your .env file with your account number.",
                )
            )

        mt5_server = self.config.mt5_server.upper() if self.config.mt5_server else ""
        if (
            not mt5_server
            or mt5_server in full_match_placeholders
            or any(p in mt5_server for p in substring_placeholders)
        ):
            self.errors.append(
                ValidationError(
                    "MT5_SERVER",
                    "MT5 server name is missing or using placeholder.",
                    True,
                    "Set MT5_SERVER in your .env (e.g., IC-Markets-Demo).",
                )
            )
        elif " " in self.config.mt5_server:
            is_critical = self.config.mode == "live"
            self.errors.append(
                ValidationError(
                    "MT5_SERVER",
                    "MT5 server name contains spaces.",
                    is_critical,
                    "Remove spaces from MT5_SERVER (e.g., Use IC-Markets-Demo instead of IC Markets Demo).",
                )
            )

        mt5_password = self.config.mt5_password.get_secret_value()
        mt5_password_up = mt5_password.upper()
        if (
            not mt5_password
            or mt5_password_up in full_match_placeholders
            or any(p in mt5_password_up for p in substring_placeholders)
        ):
            self.errors.append(
                ValidationError(
                    "MT5_PASSWORD",
                    "MT5 password is missing or using placeholder.",
                    True,
                    "Set MT5_PASSWORD in your .env file.",
                )
            )

        # Path validation for Windows
        if sys.platform == "win32":
            mt5_path = Path(self.config.mt5_path)
            if not mt5_path.exists():
                self.errors.append(
                    ValidationError(
                        "MT5_PATH",
                        f"MT5 terminal not found at: {mt5_path}.",
                        True,
                        "Verify MT5_PATH in .env. Ensure it points to terminal64.exe.",
                    )
                )

    def _check_market_settings(self) -> None:
        """Validate SYMBOL and TIMEFRAME settings."""
        if not self.config.symbol:
            self.errors.append(
                ValidationError(
                    "SYMBOL",
                    "Trading symbol is missing.",
                    True,
                    "Set SYMBOL in your .env (e.g., XAUUSD).",
                )
            )
        elif self.config.symbol != self.config.symbol.upper():
            self.errors.append(
                ValidationError(
                    "SYMBOL",
                    f"Symbol '{self.config.symbol}' should be uppercase.",
                    False,
                    f"Change SYMBOL to {self.config.symbol.upper()} in .env.",
                )
            )

        valid_timeframes = {
            "M1", "M2", "M3", "M4", "M5", "M6", "M10", "M12", "M15", "M20", "M30",
            "H1", "H2", "H3", "H4", "H6", "H8", "H12", "D1", "W1", "MN1"
        }
        if self.config.timeframe.upper() not in valid_timeframes:
            self.errors.append(
                ValidationError(
                    "TIMEFRAME",
                    f"Invalid timeframe: {self.config.timeframe}.",
                    True,
                    f"Use one of: {', '.join(sorted(valid_timeframes))}.",
                )
            )

    def _check_live_mode_confirmation(self) -> None:
        """Enforce explicit confirmation for LIVE trading."""
        if self.config.mode == "live" and self.config.confirm_live_trading.upper() != "YES":
            self.errors.append(
                ValidationError(
                    "MODE",
                    "LIVE mode detected but not confirmed.",
                    True,
                    "Use --confirm-live flag or set CONFIRM_LIVE_TRADING=YES in your environment.",
                )
            )

    def _check_placeholder_secrets(self) -> None:
        """Detect default or placeholder values in secrets."""
        # Common placeholder patterns
        placeholders = [
            "YOUR_TOKEN",
            "CHANGE_ME",
            "YOUR_ACCOUNT_ID",
            "YOUR_CHAT_ID",
            "123456789",
            "YOUR_SERVER_HERE",
            "YOUR_PASSWORD_HERE",
        ]

        # Check database URL
        default_db = "postgresql://trader:password@localhost:5432/mt5_trades"
        db_url = self.config.database_url.get_secret_value()
        if db_url == default_db or any(p in db_url.upper() for p in placeholders):
            self.errors.append(
                ValidationError(
                    "DATABASE_URL",
                    "Database URL is using default placeholder credentials.",
                    True,
                    "Update DATABASE_URL in .env with a secure password.",
                )
            )

        if self.config.mode == "live" and "sqlite" in db_url.lower():
            self.errors.append(
                ValidationError(
                    "DATABASE_URL",
                    "Using SQLite in LIVE mode is discouraged for production reliability.",
                    False,
                    "Consider using PostgreSQL for LIVE trading.",
                )
            )

        # Check Redis
        if any(p in self.config.redis_url.upper() for p in placeholders):
             self.errors.append(
                ValidationError(
                    "REDIS_URL",
                    "Redis URL contains placeholder text.",
                    True,
                    "Replace with your actual Redis connection string in .env.",
                )
            )

        # Check Telegram
        telegram_token = self.config.telegram_token.get_secret_value()
        if telegram_token and any(p in telegram_token.upper() for p in placeholders):
            self.errors.append(
                ValidationError(
                    "TELEGRAM_TOKEN",
                    "Telegram token contains placeholder text.",
                    True,
                    "Replace with your actual BotFather token in .env.",
                )
            )

        if self.config.telegram_chat_id and any(
            p in str(self.config.telegram_chat_id).upper() for p in placeholders
        ):
            self.errors.append(
                ValidationError(
                    "TELEGRAM_CHAT_ID",
                    "Telegram chat ID contains placeholder text.",
                    True,
                    "Replace with your actual chat ID in .env.",
                )
            )

        # Check MetaAPI
        metaapi_token = self.config.metaapi_token.get_secret_value()
        if metaapi_token and any(p in metaapi_token.upper() for p in placeholders):
            self.errors.append(
                ValidationError(
                    "METAAPI_TOKEN",
                    "MetaAPI token contains placeholder text.",
                    True,
                    "Replace with your actual MetaAPI token in .env.",
                )
            )

        metaapi_account_id = self.config.metaapi_account_id.get_secret_value()
        if metaapi_account_id and any(p in metaapi_account_id.upper() for p in placeholders):
            self.errors.append(
                ValidationError(
                    "METAAPI_ACCOUNT_ID",
                    "MetaAPI account ID contains placeholder text.",
                    True,
                    "Replace with your actual MetaAPI account ID in .env.",
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
                    f"Model file not found at: {self.config.model_path}.",
                    True,
                    "Ensure the model is trained or point MODEL_PATH to a valid .pt file.",
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
                    f"Risk per trade {self.config.risk_per_trade*100}% exceeds 2%.",
                    True,
                    "Reduce RISK_PER_TRADE to 0.02 (2%) or less.",
                )
            )
        elif self.config.risk_per_trade > 0.01:
            self.errors.append(
                ValidationError(
                    "RISK_PER_TRADE",
                    f"Risk per trade {self.config.risk_per_trade*100}% exceeds policy limit of 1%.",
                    False,  # Non-critical warning
                    "Consider reducing RISK_PER_TRADE to 0.01 (1%) for better risk parity.",
                )
            )

        # 2. Daily loss limits (RISK_LIMITS.md 2.1)
        # Level 4 (Emergency Stop) is 5%.
        if self.config.max_daily_loss > 0.06:
            self.errors.append(
                ValidationError(
                    "MAX_DAILY_LOSS",
                    f"Max daily loss {self.config.max_daily_loss*100}% exceeds 6%.",
                    True,
                    "Reduce MAX_DAILY_LOSS to 0.06 or less.",
                )
            )
        elif self.config.max_daily_loss > 0.05:
            self.errors.append(
                ValidationError(
                    "MAX_DAILY_LOSS",
                    f"Max daily loss {self.config.max_daily_loss*100}% exceeds 5% limit.",
                    False,
                    "Set MAX_DAILY_LOSS to 0.05 for compliance with enterprise standards.",
                )
            )

        # 3. Confidence Threshold (RISK_LIMITS.md 4.1)
        if self.config.min_confidence < 0.50:
            self.errors.append(
                ValidationError(
                    "MIN_CONFIDENCE",
                    f"Confidence threshold {self.config.min_confidence} is dangerously low.",
                    True,
                    "Set MIN_CONFIDENCE to at least 0.50.",
                )
            )
        elif self.config.min_confidence < 0.55:
            self.errors.append(
                ValidationError(
                    "MIN_CONFIDENCE",
                    f"Confidence threshold {self.config.min_confidence} is below recommended 0.55.",
                    False,
                    "Increase MIN_CONFIDENCE to 0.55 for better signal quality.",
                )
            )

        # 4. Position limits (RISK_LIMITS.md 1.1)
        # Maximum 5 open positions is the policy limit.
        if self.config.max_positions > 10:
            self.errors.append(
                ValidationError(
                    "MAX_POSITIONS",
                    f"Maximum positions {self.config.max_positions} is prohibited.",
                    True,
                    "Set MAX_POSITIONS to 10 or less.",
                )
            )
        elif self.config.max_positions > 5:
            self.errors.append(
                ValidationError(
                    "MAX_POSITIONS",
                    f"Maximum positions {self.config.max_positions} exceeds limit of 5.",
                    False,
                    "Reduce MAX_POSITIONS to 5 or less for production safety.",
                )
            )

        # 5. Leverage and Exposure (RISK_LIMITS.md 1.1)
        if self.config.max_leverage > 20:
            self.errors.append(
                ValidationError(
                    "MAX_LEVERAGE",
                    f"Max leverage {self.config.max_leverage} is too high.",
                    True,
                    "Reduce MAX_LEVERAGE to 20 or less (Policy is 10:1).",
                )
            )
        elif self.config.max_leverage > 10:
            self.errors.append(
                ValidationError(
                    "MAX_LEVERAGE",
                    f"Max leverage {self.config.max_leverage} exceeds policy limit of 10.",
                    False,
                    "Set MAX_LEVERAGE to 10 for enterprise compliance.",
                )
            )

        if self.config.max_position_size_pct > 0.20:
            self.errors.append(
                ValidationError(
                    "MAX_POSITION_SIZE_PCT",
                    f"Max position size {self.config.max_position_size_pct*100}% is dangerously high.",
                    True,
                    "Reduce MAX_POSITION_SIZE_PCT to 0.20 or less.",
                )
            )
        elif self.config.max_position_size_pct > 0.10:
            self.errors.append(
                ValidationError(
                    "MAX_POSITION_SIZE_PCT",
                    f"Max position size {self.config.max_position_size_pct*100}% exceeds 10% limit.",
                    False,
                    "Set MAX_POSITION_SIZE_PCT to 0.10 for compliance.",
                )
            )

        # 6. Drawdown Limits (RISK_LIMITS.md 6.1)
        if self.config.max_drawdown > 0.40:
            self.errors.append(
                ValidationError(
                    "MAX_DRAWDOWN",
                    f"Max drawdown {self.config.max_drawdown*100}% is unacceptable.",
                    True,
                    "Reduce MAX_DRAWDOWN to 0.40 or less.",
                )
            )
        elif self.config.max_drawdown > 0.30:
            self.errors.append(
                ValidationError(
                    "MAX_DRAWDOWN",
                    f"Max drawdown {self.config.max_drawdown*100}% exceeds 30% policy limit.",
                    False,
                    "Set MAX_DRAWDOWN to 0.30 for enterprise standards.",
                )
            )

        # 7. Stability Guards (RISK_LIMITS.md 4.2)
        if self.config.model_drift_threshold > 0.4:
            self.errors.append(
                ValidationError(
                    "MODEL_DRIFT_THRESHOLD",
                    f"Model drift threshold {self.config.model_drift_threshold} is too high.",
                    False,
                    "Set MODEL_DRIFT_THRESHOLD to 0.3 or lower.",
                )
            )

        if self.config.model_accuracy_floor < 0.45:
            self.errors.append(
                ValidationError(
                    "MODEL_ACCURACY_FLOOR",
                    f"Model accuracy floor {self.config.model_accuracy_floor} is too low.",
                    True,
                    "Set MODEL_ACCURACY_FLOOR to 0.45 or higher.",
                )
            )

        if self.config.model_win_rate_floor < 0.40:
            self.errors.append(
                ValidationError(
                    "MODEL_WIN_RATE_FLOOR",
                    f"Model win rate floor {self.config.model_win_rate_floor} is too low.",
                    True,
                    "Set MODEL_WIN_RATE_FLOOR to 0.40 or higher.",
                )
            )

    def _check_incompatible_settings(self) -> None:
        """Detect incompatible configuration combinations."""
        # 1. LIVE mode restrictions
        if self.config.mode == "live" and self.config.log_level == "DEBUG":
            self.errors.append(
                ValidationError(
                    "LOG_LEVEL",
                    "DEBUG logging in LIVE mode is discouraged.",
                    False,
                    "Set LOG_LEVEL=INFO for live trading to avoid performance issues.",
                )
            )

        if self.config.mode == "live" and self.config.max_positions > 5:
            self.errors.append(
                ValidationError(
                    "MAX_POSITIONS",
                    "Max positions > 5 is prohibited in LIVE mode.",
                    True,
                    "Set MAX_POSITIONS to 5 or less for live mode.",
                )
            )

        # 2. MetaAPI Consistency
        has_meta_token = bool(self.config.metaapi_token.get_secret_value())
        has_meta_id = bool(self.config.metaapi_account_id.get_secret_value())

        if has_meta_token and not has_meta_id:
            self.errors.append(
                ValidationError(
                    "METAAPI_ACCOUNT_ID",
                    "MetaAPI account ID is missing.",
                    True,
                    "Provide METAAPI_ACCOUNT_ID in .env alongside your token.",
                )
            )

        if has_meta_id and not has_meta_token:
            self.errors.append(
                ValidationError(
                    "METAAPI_TOKEN",
                    "MetaAPI token is missing.",
                    True,
                    "Provide METAAPI_TOKEN in .env alongside your account ID.",
                )
            )

        # 3. Telegram Consistency
        has_tele_token = bool(self.config.telegram_token.get_secret_value())
        has_tele_chat = bool(self.config.telegram_chat_id)

        if has_tele_token and not has_tele_chat:
            self.errors.append(
                ValidationError(
                    "TELEGRAM_CHAT_ID",
                    "Telegram chat ID is missing.",
                    True,
                    "Provide TELEGRAM_CHAT_ID in .env alongside your bot token.",
                )
            )

        if has_tele_chat and not has_tele_token:
            self.errors.append(
                ValidationError(
                    "TELEGRAM_TOKEN",
                    "Telegram token is missing.",
                    True,
                    "Provide TELEGRAM_TOKEN in .env alongside your chat ID.",
                )
            )

        # 4. Mode-specific warnings
        if self.config.mode == "backtest" and has_tele_token:
            self.errors.append(
                ValidationError(
                    "TELEGRAM_TOKEN",
                    "Telegram notifications are active in backtest mode.",
                    False,
                    "Comment out TELEGRAM_TOKEN during backtests to avoid noise.",
                )
            )

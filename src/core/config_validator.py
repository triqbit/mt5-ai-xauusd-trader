"""
Startup Validation Layer for MT5 AI Trading Bot.
src/core/config_validator.py
"""

import os
import stat
import sys
from pathlib import Path
from typing import NamedTuple

from src.core.config import TradingConfig
from src.core.constants import VALID_TIMEFRAME_LIST


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
        self._check_market_parameters()
        self._check_live_mode_confirmation()
        self._check_placeholder_secrets()
        self._check_model_settings()
        self._check_risk_parameters()
        self._check_exposure_limits()
        self._check_margin_and_volatility_limits()
        self._check_incompatible_settings()
        self._check_file_permissions()

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
        if self.config.mode == "live" and "DEMO" in mt5_server:
            self.errors.append(
                ValidationError(
                    "MT5_SERVER",
                    f"Demo server '{self.config.mt5_server}' used in LIVE mode.",
                    True,
                    "Use a live trading server when MODE=live.",
                )
            )

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

    def _check_market_parameters(self) -> None:
        """Verify market parameters (Symbol, Timeframe) are valid."""
        # 1. Symbol Validation
        if not self.config.symbol:
            self.errors.append(
                ValidationError(
                    "SYMBOL",
                    "Trading symbol is missing.",
                    True,
                    "Set SYMBOL in .env (e.g., XAUUSD).",
                )
            )
        elif self.config.symbol != self.config.symbol.upper():
            self.errors.append(
                ValidationError(
                    "SYMBOL",
                    f"Symbol '{self.config.symbol}' must be uppercase.",
                    True,
                    f"Change SYMBOL to '{self.config.symbol.upper()}' in .env.",
                )
            )

        # 2. Timeframe Validation
        if self.config.timeframe not in VALID_TIMEFRAME_LIST:
            self.errors.append(
                ValidationError(
                    "TIMEFRAME",
                    f"Invalid timeframe '{self.config.timeframe}'.",
                    True,
                    f"Choose one of: {', '.join(VALID_TIMEFRAME_LIST)}",
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
            "YOUR_PASSWORD",
            "PASSWORD",
            "SECRET",
            "ENTER_YOUR",
            "REPLACE_WITH",
            "EXAMPLE_TOKEN",
            "DUMMY",
            "FAKE",
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

        # Check Redis URL
        redis_url = self.config.redis_url
        if hasattr(redis_url, "get_secret_value"):
            redis_url = redis_url.get_secret_value()

        if redis_url and any(p in redis_url.upper() for p in placeholders):
            self.errors.append(
                ValidationError(
                    "REDIS_URL",
                    "Redis URL contains placeholder text.",
                    True,
                    "Update REDIS_URL in .env with your actual Redis connection string.",
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

        # 2.1 Daily Loss Hierarchy (RISK_LIMITS.md 11.1)
        # Ensure L1 < L2 < L3 < L4 (max_daily_loss) < Hard Stop
        levels = [
            ("DAILY_LOSS_LVL1", self.config.daily_loss_lvl1),
            ("DAILY_LOSS_LVL2", self.config.daily_loss_lvl2),
            ("DAILY_LOSS_LVL3", self.config.daily_loss_lvl3),
            ("MAX_DAILY_LOSS", self.config.max_daily_loss),
            ("DAILY_LOSS_HARD_STOP", self.config.daily_loss_hard_stop),
        ]

        for i in range(len(levels) - 1):
            if levels[i][1] >= levels[i + 1][1]:
                self.errors.append(
                    ValidationError(
                        levels[i + 1][0],
                        f"{levels[i+1][0]} ({levels[i+1][1]}) must be greater than {levels[i][0]} ({levels[i][1]}).",
                        True,
                        "Correct the daily loss hierarchy in .env.",
                    )
                )

        # 2.2 Weekly/Monthly Loss Limits (RISK_LIMITS.md 3.1, 3.2)
        if self.config.max_weekly_loss > 0.15:
            self.errors.append(
                ValidationError(
                    "MAX_WEEKLY_LOSS",
                    f"Max weekly loss {self.config.max_weekly_loss*100}% exceeds 15% safety limit.",
                    True,
                    "Reduce MAX_WEEKLY_LOSS to 0.15 or less.",
                )
            )

        if self.config.max_monthly_loss > 0.25:
            self.errors.append(
                ValidationError(
                    "MAX_MONTHLY_LOSS",
                    f"Max monthly loss {self.config.max_monthly_loss*100}% exceeds 25% safety limit.",
                    True,
                    "Reduce MAX_MONTHLY_LOSS to 0.25 or less.",
                )
            )

        if self.config.max_weekly_loss >= self.config.max_monthly_loss:
            self.errors.append(
                ValidationError(
                    "MAX_MONTHLY_LOSS",
                    f"Max monthly loss ({self.config.max_monthly_loss}) must be greater than weekly loss ({self.config.max_weekly_loss}).",
                    True,
                    "Correct the loss limit hierarchy in .env.",
                )
            )

        # 2.3 Spread Hierarchy (RISK_LIMITS.md 5.2)
        spread_levels = [
            ("MIN_SPREAD_PIPS", self.config.min_spread_pips),
            ("SPREAD_ALERT_PIPS", self.config.spread_alert_pips),
            ("SPREAD_REDUCE_PIPS", self.config.spread_reduce_pips),
            ("SPREAD_HALT_PIPS", self.config.spread_halt_pips),
        ]

        for i in range(len(spread_levels) - 1):
            if spread_levels[i][1] >= spread_levels[i + 1][1]:
                self.errors.append(
                    ValidationError(
                        spread_levels[i + 1][0],
                        f"{spread_levels[i+1][0]} ({spread_levels[i+1][1]}) must be greater than {spread_levels[i][0]} ({spread_levels[i][1]}).",
                        True,
                        "Correct the spread limit hierarchy in .env.",
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
        if self.config.model_drift_threshold > 0.3:
            self.errors.append(
                ValidationError(
                    "MODEL_DRIFT_THRESHOLD",
                    f"Model drift threshold {self.config.model_drift_threshold} is above recommended 0.3.",
                    False,
                    "Set MODEL_DRIFT_THRESHOLD to 0.3 or lower for better stability.",
                )
            )

        if self.config.model_accuracy_floor < 0.50:
            self.errors.append(
                ValidationError(
                    "MODEL_ACCURACY_FLOOR",
                    f"Model accuracy floor {self.config.model_accuracy_floor} is below 0.50.",
                    True,
                    "Set MODEL_ACCURACY_FLOOR to 0.50 or higher (Policy Limit).",
                )
            )

        if self.config.model_win_rate_floor < 0.45:
            self.errors.append(
                ValidationError(
                    "MODEL_WIN_RATE_FLOOR",
                    f"Model win rate floor {self.config.model_win_rate_floor} is below 0.45.",
                    True,
                    "Set MODEL_WIN_RATE_FLOOR to 0.45 or higher (Policy Limit).",
                )
            )

        # 8. Calibration Threshold (RISK_LIMITS.md 4.2)
        # Release-readiness gate: Prevents deployment of overconfident/poorly calibrated models.
        # High ECE (Expected Calibration Error) indicates the model's confidence doesn't match its accuracy.
        if self.config.model_calibration_threshold > 0.25:
            self.errors.append(
                ValidationError(
                    "MODEL_CALIBRATION_THRESHOLD",
                    f"Model calibration threshold {self.config.model_calibration_threshold} exceeds 0.25 limit.",
                    True,
                    "Set MODEL_CALIBRATION_THRESHOLD to 0.25 or lower for enterprise compliance.",
                )
            )

    def _check_exposure_limits(self) -> None:
        """Verify exposure and notional limits (RISK_LIMITS.md 1.2)."""
        if self.config.max_single_direction_pct > 0.50:
            self.errors.append(
                ValidationError(
                    "MAX_SINGLE_DIRECTION_PCT",
                    f"Max single direction exposure {self.config.max_single_direction_pct*100}% is too high.",
                    True,
                    "Reduce MAX_SINGLE_DIRECTION_PCT to 0.50 or less (Policy is 0.30).",
                )
            )
        elif self.config.max_single_direction_pct > 0.30:
            self.errors.append(
                ValidationError(
                    "MAX_SINGLE_DIRECTION_PCT",
                    f"Max single direction exposure {self.config.max_single_direction_pct*100}% exceeds 30% policy.",
                    False,
                    "Set MAX_SINGLE_DIRECTION_PCT to 0.30 for compliance.",
                )
            )

        if self.config.max_total_notional_pct > 1.50:
            self.errors.append(
                ValidationError(
                    "MAX_TOTAL_NOTIONAL_PCT",
                    f"Max total notional {self.config.max_total_notional_pct*100}% is dangerously high.",
                    True,
                    "Reduce MAX_TOTAL_NOTIONAL_PCT to 1.50 or less.",
                )
            )
        elif self.config.max_total_notional_pct > 1.00:
            self.errors.append(
                ValidationError(
                    "MAX_TOTAL_NOTIONAL_PCT",
                    f"Max total notional {self.config.max_total_notional_pct*100}% exceeds 100% equity.",
                    False,
                    "Set MAX_TOTAL_NOTIONAL_PCT to 1.00 for enterprise safety.",
                )
            )

        # Max Trades Per Day validation (Plan requirement)
        if self.config.max_trades_per_day > 50:
            self.errors.append(
                ValidationError(
                    "MAX_TRADES_PER_DAY",
                    f"Max trades per day ({self.config.max_trades_per_day}) exceeds institutional limit of 50.",
                    True,
                    "Reduce MAX_TRADES_PER_DAY to 50 or less.",
                )
            )

        # Min Lot Size validation (Plan requirement)
        if self.config.min_lot_size < 0.01:
            self.errors.append(
                ValidationError(
                    "MIN_LOT_SIZE",
                    f"Min lot size ({self.config.min_lot_size}) is below 0.01.",
                    True,
                    "Set MIN_LOT_SIZE to 0.01 or higher to avoid rounding issues.",
                )
            )

    def _check_margin_and_volatility_limits(self) -> None:
        """Verify margin and volatility hierarchy levels (RISK_LIMITS.md 1.2, 5.1)."""
        # 1. Margin Hierarchy (Note: These are utilization percentages, not MT5 Margin Level %)
        # As risk increases, utilization grows: Alert (70%) < Halt (80%) < Liquidation (90%)
        margin_levels = [
            ("MARGIN_ALERT_PCT", self.config.margin_alert_pct),
            ("MARGIN_HALT_PCT", self.config.margin_halt_pct),
            ("MARGIN_LIQUIDATION_PCT", self.config.margin_liquidation_pct),
        ]

        for i in range(len(margin_levels) - 1):
            if margin_levels[i][1] >= margin_levels[i + 1][1]:
                self.errors.append(
                    ValidationError(
                        margin_levels[i + 1][0],
                        f"{margin_levels[i+1][0]} ({margin_levels[i+1][1]}) must be greater than {margin_levels[i][0]} ({margin_levels[i][1]}).",
                        True,
                        "Correct the margin limit hierarchy in .env.",
                    )
                )

        # 2. Volatility Hierarchy
        vol_levels = [
            ("VOLATILITY_HIGH_THRESHOLD", self.config.volatility_high_threshold),
            ("VOLATILITY_VERY_HIGH_THRESHOLD", self.config.volatility_very_high_threshold),
            ("VOLATILITY_EXTREME_THRESHOLD", self.config.volatility_extreme_threshold),
        ]

        for i in range(len(vol_levels) - 1):
            if vol_levels[i][1] >= vol_levels[i + 1][1]:
                self.errors.append(
                    ValidationError(
                        vol_levels[i + 1][0],
                        f"{vol_levels[i+1][0]} ({vol_levels[i+1][1]}) must be greater than {vol_levels[i][0]} ({vol_levels[i][1]}).",
                        True,
                        "Correct the volatility threshold hierarchy in .env.",
                    )
                )

    def _check_incompatible_settings(self) -> None:
        """Detect incompatible configuration combinations."""
        # 0. Database Choice
        if (
            self.config.mode == "live"
            and "sqlite" in self.config.database_url.get_secret_value().lower()
        ):
            self.errors.append(
                ValidationError(
                    "DATABASE_URL",
                    "SQLite is used in LIVE mode.",
                    False,  # Warning
                    "Consider using a production-grade database like PostgreSQL for live trading.",
                )
            )

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

    def _check_file_permissions(self) -> None:
        """Verify sensitive files have restrictive permissions (Linux/Mac only)."""
        if sys.platform == "win32":
            return

        sensitive_files = [
            Path(".env"),
            Path("trades.db"),
            Path("audit.db"),
            self.config.model_config.get("env_file"),
        ]

        # Filter out None and duplicates
        unique_paths = {Path(p).resolve() for p in sensitive_files if p and Path(p).exists()}

        for path in unique_paths:
            try:
                mode = os.stat(path).st_mode
                # Check if group or others have any permissions (0o077 mask)
                if mode & (stat.S_IRWXG | stat.S_IRWXO):
                    current_mode = oct(stat.S_IMODE(mode))
                    self.errors.append(
                        ValidationError(
                            "FILE_PERMISSION",
                            f"Insecure permissions for {path.name}: {current_mode}",
                            False,  # Warning for now to avoid breaking existing setups
                            f"Run 'chmod 600 {path.name}' to restrict access.",
                        )
                    )
            except Exception:
                # Log but don't fail if we can't check permissions
                pass

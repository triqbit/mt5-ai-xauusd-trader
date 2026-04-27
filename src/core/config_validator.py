"""
MT5 AI/ML Trading Bot - Startup Validation Layer
src/core/config_validator.py
"""
from __future__ import annotations

from typing import List

from pydantic import BaseModel

from src.core.config import TradingConfig


class ValidationResult(BaseModel):
    """Container for validation status and messages."""
    is_valid: bool
    errors: List[str]
    warnings: List[str]


def validate_config(cfg: TradingConfig) -> ValidationResult:
    """
    Performs deep validation of the trading configuration.
    Returns a ValidationResult containing any errors or warnings.
    """
    errors: List[str] = []
    warnings: List[str] = []

    # 1. MT5 Credentials
    if cfg.mt5_login <= 0:
        errors.append(f"MT5_LOGIN must be a positive integer, got {cfg.mt5_login}")
    if not cfg.mt5_server or cfg.mt5_server.lower() in ("test", "server", ""):
        errors.append(f"MT5_SERVER is invalid or placeholder: '{cfg.mt5_server}'")

    # 2. Secret Placeholders
    placeholders = ("password", "123456", "secret", "change_me", "test")
    if cfg.mt5_password.lower() in placeholders:
        errors.append("MT5_PASSWORD is using a common placeholder value.")
    if cfg.database_url and "password" in cfg.database_url.lower() and "trader:password" in cfg.database_url:
        warnings.append("DATABASE_URL appears to use the default 'trader:password' credential.")

    # 3. Live Mode Restrictions
    if cfg.mode == "live":
        # Requires explicit environment variable confirmation
        if not cfg.confirm_live_trading:
            errors.append("LIVE mode detected but CONFIRM_LIVE_TRADING is not set to 'true'.")

        # Incompatible combinations: Live mode should ideally not use SQLite
        if "sqlite" in cfg.database_url.lower():
            warnings.append("LIVE mode is active but using SQLite. PostgreSQL is recommended for production.")

    # 4. Risk Parameters (Safe Ranges)
    if cfg.risk_per_trade > 0.02:
        # This is also caught by Pydantic validator in config.py, but we double-check here
        errors.append(f"risk_per_trade {cfg.risk_per_trade} exceeds production limit of 0.02 (2%)")

    if cfg.max_daily_loss > 0.10:
        warnings.append(f"max_daily_loss {cfg.max_daily_loss} is high (>10%). Ensure this is intentional.")

    if cfg.max_positions > 5 and cfg.mode == "live":
        warnings.append(f"max_positions {cfg.max_positions} is high for live trading. Monitor margin carefully.")

    # 5. Model Path
    if not cfg.model_path.exists():
        errors.append(f"Model path does not exist: {cfg.model_path}")

    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings
    )

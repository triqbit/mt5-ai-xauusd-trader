"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/core/config.py
Centralised Pydantic-v2 settings loaded from environment variables
or a .env file. All secrets stay out of the codebase.

Author: triqbit
License: MIT
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]  # repo root


class TradingConfig(BaseSettings):
    """
    Enterprise-grade configuration management for the MT5 AI Trading Bot.

    This class uses Pydantic Settings V2 to load environment variables and
    enforce strict validation on all trading and risk parameters.

    Attributes:
        mt5_login (int): MT5 account number.
        mt5_password (SecretStr): MT5 account password.
        mt5_server (str): MT5 broker server address.
        mt5_path (str): Path to the MT5 terminal executable.
        metaapi_token (SecretStr): MetaAPI cloud authentication token.
        metaapi_account_id (SecretStr): MetaAPI cloud account identifier.
        symbol (str): Financial instrument to trade (e.g., XAUUSD).
        timeframe (str): Chart timeframe for analysis.
        mode (str): Execution mode (demo, live, backtest).
        max_positions (int): Maximum concurrent open positions.
        risk_per_trade (float): Risk fraction per trade (e.g., 0.01 = 1%).
        max_position_size_pct (float): Max size as % of equity.
        min_lot_size (float): Minimum permitted lot size.
        max_leverage (float): Maximum account leverage limit.
        max_single_direction_pct (float): Max exposure in one direction.
        max_total_notional_pct (float): Max total notional exposure.
        margin_alert_pct (float): Margin level for alerts.
        margin_halt_pct (float): Margin level to stop trading.
        margin_liquidation_pct (float): Margin level for force closure.
        max_drawdown (float): Maximum allowed equity drawdown.
        max_daily_loss (float): Hard daily loss limit (Level 4).
        daily_loss_lvl1 (float): Yellow alert daily loss level.
        daily_loss_lvl2 (float): Orange alert daily loss level.
        daily_loss_lvl3 (float): Red alert daily loss level.
        daily_loss_hard_stop (float): Hard stop daily loss level.
        daily_win_cap (float): Maximum daily profit target.
        max_trades_per_day (int): Limit on daily trade count.
        max_losing_streak (int): Stop after X consecutive losses.
        max_winning_streak (int): Alert after X consecutive wins.
        max_weekly_loss (float): Weekly loss circuit breaker.
        max_monthly_loss (float): Monthly loss circuit breaker.
        volatility_high_threshold (float): ATR ratio for high volatility.
        volatility_very_high_threshold (float): ATR ratio for very high volatility.
        volatility_extreme_threshold (float): ATR ratio for extreme volatility.
        max_slippage_pips (float): Max allowed order slippage.
        min_spread_pips (float): Minimum spread for trading.
        spread_alert_pips (float): Spread level for warnings.
        spread_reduce_pips (float): Spread level to reduce sizing.
        spread_halt_pips (float): Spread level to halt trading.
        algorithm (str): ML algorithm to use.
        model_path (Path): Path to model weights.
        train_steps (int): Total training steps.
        device (str): Device for inference (cpu, cuda, etc.).
        database_url (SecretStr): DB connection string.
        redis_url (str): Redis connection string.
        prometheus_port (int): Metrics port.
        dashboard_port (int): UI port.
        log_level (str): Logging verbosity.
        telegram_token (SecretStr): Telegram bot token.
        telegram_chat_id (str): Telegram recipient ID.
        confirm_live_trading (str): Safety flag for live mode.
        min_confidence (float): Signal confidence floor.
        confidence_threshold (float): Alert threshold for confidence.
        consensus_threshold (float): Ensemble agreement threshold.
        model_drift_threshold (float): Alert threshold for model drift.
        model_accuracy_floor (float): Min acceptable model accuracy.
        model_win_rate_floor (float): Min acceptable historical win rate.
        model_calibration_threshold (float): Max acceptable calibration error.
        data_freshness_threshold (int): Max age of market data in seconds.
        signal_flicker_window (int): Lookback for signal stability.
        max_signal_changes (int): Max allowed changes in window.
    """

    model_config = SettingsConfigDict(
        env_file=ROOT / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── MT5 Connection ──────────────────────────────────────────────────────────
    mt5_login: int = Field(
        default=0, description="MT5 account number for login", validation_alias="MT5_LOGIN"
    )
    mt5_password: SecretStr = Field(
        ..., description="MT5 account password for authentication", validation_alias="MT5_PASSWORD"
    )
    mt5_server: str = Field(
        ..., description="MT5 broker server name (e.g., Broker-Demo)", validation_alias="MT5_SERVER"
    )
    mt5_path: str = Field(
        default="C:/Program Files/MetaTrader 5/terminal64.exe",
        description="Full path to the MT5 terminal executable (Windows only)",
    )

    # ── MetaAPI (cloud fallback) ─────────────────────────────────────────────────
    metaapi_token: SecretStr = Field(
        default="", description="Authentication token for MetaAPI cloud services"
    )
    metaapi_account_id: SecretStr = Field(
        default="", description="Unique account identifier for MetaAPI provisioning"
    )

    # ── Trading parameters ─────────────────────────────────────────────────────
    symbol: str = Field(
        default="XAUUSD",
        description="The financial instrument to trade (e.g., XAUUSD)",
        validation_alias="SYMBOL",
    )
    timeframe: str = Field(
        default="M5", description="The chart timeframe for analysis (e.g., M5, H1)"
    )
    mode: Literal["demo", "live", "backtest"] = Field(
        default="demo",
        description="Execution mode: demo, live, or backtest",
        validation_alias="MODE",
    )

    # ── Risk Parameters (per RISK_LIMITS.md) ──────────────────────────────────
    max_positions: int = Field(
        default=5, ge=1, le=10, description="Maximum number of concurrent open positions permitted"
    )
    risk_per_trade: float = Field(
        default=0.01,
        ge=0.001,
        le=0.02,
        description="Fraction of account equity to risk per trade (e.g., 0.01 = 1%)",
    )
    max_position_size_pct: float = Field(
        default=0.10, description="Max Position Size: 10% of account equity per trade"
    )
    min_lot_size: float = Field(default=0.01, description="Min Position Size: 0.01 lot")
    max_leverage: float = Field(default=10.0, description="Max Leverage: 10:1")

    # Exposure Limits
    max_single_direction_pct: float = Field(default=0.30, description="Max 30% net long OR short")
    max_total_notional_pct: float = Field(default=1.00, description="<100% of account equity")
    margin_alert_pct: float = Field(default=0.70, description="Alert at 70% margin utilization")
    margin_halt_pct: float = Field(
        default=0.80, description="Halt trading at 80% margin utilization"
    )
    margin_liquidation_pct: float = Field(default=0.90, description="Automatic close at 90% margin")
    max_drawdown: float = Field(default=0.30, description="Max Equity Drawdown (30%)")

    # Daily Limits (Cascading)
    max_daily_loss: float = Field(
        default=0.05, ge=0.01, le=0.06, description="Emergency Stop Level 4: 5% loss"
    )
    daily_loss_lvl1: float = Field(default=0.02, description="Level 1 (Yellow Alert): 2% loss")
    daily_loss_lvl2: float = Field(default=0.03, description="Level 2 (Orange Alert): 3% loss")
    daily_loss_lvl3: float = Field(default=0.04, description="Level 3 (Red Alert): 4% loss")
    daily_loss_hard_stop: float = Field(default=0.06, description="Hard Stop: 6% loss")
    daily_win_cap: float = Field(default=0.10, description="Daily Win Cap: 10%")
    max_trades_per_day: int = Field(default=20, description="Max 20 trades per day")
    max_losing_streak: int = Field(default=3, description="Halt trading after 3 consecutive losses")
    max_winning_streak: int = Field(default=5, description="Alert after 5 consecutive wins")

    # Weekly/Monthly Limits
    max_weekly_loss: float = Field(default=0.10, description="Max Weekly Loss: 10% of account")
    max_monthly_loss: float = Field(default=0.15, description="Max Monthly Loss: 15% of account")

    # Volatility Thresholds
    volatility_high_threshold: float = Field(
        default=1.5, description="High Volatility (>1.5x normal)"
    )
    volatility_very_high_threshold: float = Field(
        default=2.0, description="Very High Volatility (>2x normal)"
    )
    volatility_extreme_threshold: float = Field(
        default=3.0, description="Extreme Volatility (>3x normal)"
    )

    # Execution
    max_slippage_pips: float = Field(default=1.0, description="Max Acceptable Slippage: 1.0 pip")
    min_spread_pips: float = Field(default=0.5, description="Min Bid-Ask Spread: <0.5 pips")
    spread_alert_pips: float = Field(default=1.0, description="Alert if spread >1.0 pip")
    spread_reduce_pips: float = Field(default=1.5, description="Reduce if spread >1.5 pips")
    spread_halt_pips: float = Field(default=2.0, description="Halt if spread >2.0 pips")

    # ── Model ──────────────────────────────────────────────────────────────────
    algorithm: Literal["ppo", "dreamer", "lstm", "ensemble"] = Field(
        default="ensemble", description="The ML algorithm architecture to use for signal generation"
    )
    model_path: Path = Field(
        default=ROOT / "models" / "trained" / "ensemble_latest.pt",
        description="Path to the serialized weights of the trained model",
    )
    train_steps: int = Field(
        default=1_000_000, ge=100_000, description="Number of environment steps for model training"
    )
    device: Literal["cpu", "cuda", "mps", "auto"] = Field(
        default="auto",
        description="Hardware accelerator for model inference (cpu, cuda, mps, auto)",
    )

    # ── Database ────────────────────────────────────────────────────────────
    database_url: SecretStr = Field(
        default="postgresql://trader:password@localhost:5432/mt5_trades",
        description="SQLAlchemy-compatible connection string for the primary database",
    )
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Connection URL for the Redis instance used for caching/queuing",
    )

    # ── Monitoring ──────────────────────────────────────────────────────────
    prometheus_port: int = Field(
        default=8000, description="Network port for exposing Prometheus metrics"
    )
    dashboard_port: int = Field(
        default=8050, description="Network port for the interactive monitoring dashboard"
    )
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(
        default="INFO", description="Granularity of application logs (DEBUG, INFO, WARNING, ERROR)"
    )
    telegram_token: SecretStr = Field(
        default="", description="Access token for the Telegram Bot API for real-time alerts"
    )
    telegram_chat_id: str = Field(
        default="", description="Telegram Chat ID or Group ID where alerts will be sent"
    )
    confirm_live_trading: str = Field(
        default="",
        description="Explicit confirmation for LIVE trading (must be 'YES' to start in live mode)",
    )

    # Prediction Limits
    min_confidence: float = Field(
        default=0.55,
        ge=0.5,
        le=1.0,
        description="Minimum model confidence score required to execute a signal",
    )
    confidence_threshold: float = Field(
        default=0.60,
        ge=0.1,
        le=1.0,
        description="Confidence level below which a warning alert is triggered",
    )
    consensus_threshold: float = Field(
        default=0.60, ge=0.5, le=1.0, description="Need 60%+ agreement across ensemble"
    )

    model_drift_threshold: float = Field(
        default=0.3,
        ge=0.05,
        le=0.5,
        description="Maximum allowed model drift score before halting trades",
    )
    model_accuracy_floor: float = Field(
        default=0.5,
        ge=0.5,
        le=0.9,
        description="Minimum allowed model accuracy score before halting trades",
    )
    model_win_rate_floor: float = Field(
        default=0.45,
        ge=0.4,
        le=0.7,
        description="Minimum allowed historical win rate before halting trades",
    )
    model_calibration_threshold: float = Field(
        default=0.25,
        ge=0.05,
        le=0.5,
        description="Maximum allowed model calibration error (ECE) before halting trades",
    )
    data_freshness_threshold: int = Field(
        default=300, ge=60, description="Maximum age of market data in seconds before alerting"
    )

    signal_flicker_window: int = Field(
        default=6, ge=2, le=20, description="Window size for signal flicker detection"
    )
    max_signal_changes: int = Field(
        default=3, ge=1, le=10, description="Maximum allowed signal direction changes in window"
    )

    @field_validator("risk_per_trade")
    @classmethod
    def risk_must_be_safe(cls, v: float) -> float:
        """Validate that risk per trade does not exceed 2%."""
        if v > 0.02:
            raise ValueError("risk_per_trade > 2% is not permitted in production.")
        return v

    @property
    def is_live(self) -> bool:
        """Check if the system is running in live trading mode."""
        return self.mode == "live"

    @property
    def data_dir(self) -> Path:
        """Return the path to the data directory."""
        return ROOT / "data"

    @property
    def logs_dir(self) -> Path:
        """Return the path to the logs directory."""
        return ROOT / "logs"


@lru_cache(maxsize=1)
def get_config() -> TradingConfig:
    """
    Retrieve the singleton TradingConfig instance.

    Returns:
        TradingConfig: The cached configuration object.
    """
    return TradingConfig()  # type: ignore[call-arg]


__all__ = ["TradingConfig", "get_config"]

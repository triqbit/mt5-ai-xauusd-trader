"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/core/config.py
Centralised Pydantic-v2 settings loaded from environment variables
or a .env file. All secrets stay out of the codebase.
Author : triqbit
License: MIT
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.core.constants import SYMBOL_PATTERN, VALID_TIMEFRAMES

ROOT = Path(__file__).resolve().parents[2]  # repo root


class TradingConfig(BaseSettings):
    """Runtime-configurable trading parameters."""

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
        pattern=SYMBOL_PATTERN,
        description="The financial instrument to trade (e.g., XAUUSD)",
        validation_alias="SYMBOL",
    )
    timeframe: VALID_TIMEFRAMES = Field(
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

    # Macro Risk Settings
    enable_macro_guard: bool = Field(
        default=True, description="Enable automatic execution blocking during high-impact events"
    )
    macro_pre_event_minutes: dict[int, int] = Field(
        default_factory=lambda: {1: 5, 2: 15, 3: 60, 4: 120},
        description="Minutes before an event to begin risk reduction/blocking, indexed by Impact Level",
    )
    macro_post_event_minutes: dict[int, int] = Field(
        default_factory=lambda: {1: 5, 2: 30, 3: 120, 4: 240},
        description="Minutes after an event to maintain risk reduction/blocking, indexed by Impact Level",
    )

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

    # Capital Allocation
    allocator_max_total_heat: float = Field(default=0.70, description="Max 70% of budget committed")
    allocator_max_symbol_risk: float = Field(default=0.40, description="Max 40% per symbol")
    allocator_max_family_risk: float = Field(default=0.40, description="Max 40% per model family")
    allocator_performance_step: float = Field(default=0.05, description="Adjustment step for performance")
    allocator_decay_rate: float = Field(default=0.001, description="Rate at which multiplier returns to 1.0")
    allocator_soft_limit_buffer: float = Field(default=0.10, description="Buffer for diversification guard")

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
    execution_latency_threshold: float = Field(
        default=1.0, description="Max allowed execution latency in seconds before alerting"
    )

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
    redis_url: SecretStr = Field(
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
    outcome_noise_threshold: float = Field(
        default=0.0001,
        description="Threshold for price change to be considered significant for outcome tracking (e.g. 0.0001 = 1 pip for XAUUSD)",
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
        if v > 0.02:
            raise ValueError("risk_per_trade > 2% is not permitted in production.")
        return v

    @property
    def is_live(self) -> bool:
        return self.mode == "live"

    @property
    def data_dir(self) -> Path:
        return ROOT / "data"

    @property
    def logs_dir(self) -> Path:
        return ROOT / "logs"


@lru_cache(maxsize=1)
def get_config() -> TradingConfig:
    """Return singleton TradingConfig (cached after first call)."""
    return TradingConfig()  # type: ignore[call-arg]


__all__ = ["TradingConfig", "get_config"]

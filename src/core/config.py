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
    mt5_login: int = Field(default=0, description="MT5 account number for login")
    mt5_password: SecretStr = Field(..., description="MT5 account password for authentication")
    mt5_server: str = Field(..., description="MT5 broker server name (e.g., Broker-Demo)")
    mt5_path: str = Field(
        default="C:/Program Files/MetaTrader 5/terminal64.exe",
        description="Full path to the MT5 terminal executable (Windows only)",
    )

    # ── MetaAPI (cloud fallback) ─────────────────────────────────────────────────
    metaapi_token: SecretStr = Field(
        default=SecretStr(""), description="Authentication token for MetaAPI cloud services"
    )
    metaapi_account_id: str = Field(default="", description="Unique account identifier for MetaAPI provisioning")

    # ── Trading parameters ─────────────────────────────────────────────────────
    symbol: str = Field(default="XAUUSD", description="The financial instrument to trade (e.g., XAUUSD)")
    timeframe: str = Field(default="M5", description="The chart timeframe for analysis (e.g., M5, H1)")
    mode: Literal["demo", "live", "backtest"] = Field(
        default="demo", description="Execution mode: demo, live, or backtest"
    )
    max_positions: int = Field(
        default=3, ge=1, le=5, description="Maximum number of concurrent open positions permitted"
    )
    risk_per_trade: float = Field(
        default=0.01, ge=0.001, le=0.02, description="Fraction of account equity to risk per trade (e.g., 0.01 = 1%)"
    )
    max_daily_loss: float = Field(
        default=0.05, ge=0.01, le=0.06, description="Maximum daily drawdown percentage before halting trading"
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
        default="auto", description="Hardware accelerator for model inference (cpu, cuda, mps, auto)"
    )

    # ── Database ────────────────────────────────────────────────────────────
    database_url: SecretStr = Field(
        default=SecretStr("postgresql://trader:password@localhost:5432/mt5_trades"),
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
        default=SecretStr(""), description="Access token for the Telegram Bot API for real-time alerts"
    )
    telegram_chat_id: str = Field(
        default="", description="Telegram Chat ID or Group ID where alerts will be sent"
    )
    confirm_live_trading: str = Field(
        default="", description="Explicit confirmation for LIVE trading (must be 'YES' to start in live mode)"
    )
    confidence_threshold: float = Field(
        default=0.6, ge=0.5, le=1.0, description="Minimum model confidence score required to execute a signal"
    )
    model_drift_threshold: float = Field(
        default=0.3, ge=0.05, le=0.5, description="Maximum allowed model drift score before halting trades"
    )
    model_accuracy_floor: float = Field(
        default=0.5, ge=0.5, le=0.9, description="Minimum allowed model accuracy score before halting trades"
    )
    model_win_rate_floor: float = Field(
        default=0.45, ge=0.4, le=0.7, description="Minimum allowed historical win rate before halting trades"
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
    return TradingConfig()


__all__ = ["TradingConfig", "get_config"]

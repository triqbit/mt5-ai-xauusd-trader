"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/core/config.py
Centralized Pydantic-v2 settings loaded from environment variables
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
    mt5_login: int = Field(default=0, description="MT5 account number for login", validation_alias="MT5_LOGIN")
    mt5_password: SecretStr = Field(default=SecretStr(""), description="MT5 account password", validation_alias="MT5_PASSWORD")
    mt5_server: str = Field(default="", description="MT5 broker server name", validation_alias="MT5_SERVER")
    mt5_path: str = Field(
        default="C:/Program Files/MetaTrader 5/terminal64.exe",
        description="Full path to the MT5 terminal executable",
    )

    # ── MetaAPI (cloud fallback) ─────────────────────────────────────────────────
    metaapi_token: SecretStr = Field(default=SecretStr(""), description="MetaAPI auth token")
    metaapi_account_id: str = Field(default="", description="MetaAPI account identifier")

    # ── Trading parameters ─────────────────────────────────────────────────────
    symbol: str = Field(default="XAUUSD", description="Symbol to trade", validation_alias="SYMBOL")
    timeframe: str = Field(default="M5", description="Chart timeframe")
    mode: Literal["demo", "live", "backtest"] = Field(
        default="demo", description="Execution mode", validation_alias="MODE"
    )
    max_positions: int = Field(
        default=3, ge=1, le=10, description="Max concurrent positions"
    )
    risk_per_trade: float = Field(
        default=0.01, ge=0.001, le=0.05, description="Fraction of equity to risk per trade"
    )
    max_daily_loss: float = Field(
        default=0.05, ge=0.01, le=0.20, description="Max daily drawdown fraction"
    )

    # ── Model ──────────────────────────────────────────────────────────────────
    algorithm: Literal["ppo", "dreamer", "lstm", "ensemble"] = Field(
        default="ensemble", description="ML algorithm to use"
    )
    model_path: Path = Field(
        default=ROOT / "models" / "trained" / "ensemble_latest.pt",
        description="Path to trained model weights",
    )
    device: Literal["cpu", "cuda", "mps", "auto"] = Field(
        default="auto", description="Hardware accelerator"
    )

    # ── Database ────────────────────────────────────────────────────────────
    database_url: SecretStr = Field(
        default=SecretStr("postgresql://trader:password@localhost:5432/mt5_trades"),
        description="Primary database connection string",
    )

    # ── Monitoring ──────────────────────────────────────────────────────────
    prometheus_port: int = Field(default=8000, description="Prometheus metrics port")
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(
        default="INFO", description="Logging granularity"
    )
    telegram_token: SecretStr = Field(default=SecretStr(""), description="Telegram bot token")
    telegram_chat_id: str = Field(default="", description="Telegram chat ID")

    # Backward compatibility fields for health checks
    confirm_live_trading: str = Field(default="", description="Confirm live trading")
    confidence_threshold: float = Field(default=0.6, description="Confidence threshold")

    @field_validator("risk_per_trade")
    @classmethod
    def risk_must_be_safe(cls, v: float) -> float:
        if v > 0.02:
            raise ValueError("risk_per_trade > 2% is not permitted in production.")
        return v

    @property
    def is_live(self) -> bool:
        return self.mode == "live"


@lru_cache(maxsize=1)
def get_config() -> TradingConfig:
    """Return singleton TradingConfig."""
    return TradingConfig()  # type: ignore[call-arg]


__all__ = ["TradingConfig", "get_config"]

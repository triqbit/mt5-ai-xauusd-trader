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

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]  # repo root


class TradingConfig(BaseSettings):
    """Runtime-configurable trading parameters."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── MT5 Connection ──────────────────────────────────────────────────────────
    mt5_login: int = Field(default=0, description="MT5 account number")
    mt5_password: str = Field(..., description="MT5 account password")
    mt5_server: str = Field(..., description="Broker server name")
    mt5_path: str = Field(
        default="C:/Program Files/MetaTrader 5/terminal64.exe",
        description="Path to MT5 terminal executable (Windows only)",
    )

    # ── MetaAPI (cloud fallback) ─────────────────────────────────────────────────
    metaapi_token: str = Field(default="", description="MetaAPI cloud token")
    metaapi_account_id: str = Field(default="", description="MetaAPI account ID")

    # ── Trading parameters ─────────────────────────────────────────────────────
    symbol: str = Field(default="XAUUSD", description="Primary trading symbol")
    timeframe: str = Field(default="M5", description="Primary chart timeframe")
    mode: Literal["demo", "live", "backtest"] = Field(default="demo", description="Execution mode")

    # ── Risk Parameters (as per RISK_LIMITS.md) ────────────────────────────────
    max_positions: int = Field(default=5, ge=1, le=10, description="Max concurrent positions")
    risk_per_trade: float = Field(default=0.01, ge=0.001, le=0.02, description="Max risk % per trade (0.01 = 1%)")
    max_leverage: float = Field(default=10.0, ge=1.0, le=50.0, description="Max allowed leverage")

    # Daily cascading loss limits
    daily_loss_limit_lvl1: float = Field(default=0.02, description="2% loss -> Alert")
    daily_loss_limit_lvl2: float = Field(default=0.03, description="3% loss -> Half position size")
    daily_loss_limit_lvl3: float = Field(default=0.04, description="4% loss -> Quarter position size")
    daily_loss_limit_lvl4: float = Field(default=0.05, description="5% loss -> Halt trading")
    daily_loss_limit_hard: float = Field(default=0.06, description="6% loss -> Force close all")

    # Drawdown limits
    drawdown_limit_lvl1: float = Field(default=0.10, description="10% drawdown -> Alert")
    drawdown_limit_lvl2: float = Field(default=0.15, description="15% drawdown -> 75% position size")
    drawdown_limit_lvl3: float = Field(default=0.20, description="20% drawdown -> 50% position size")
    drawdown_limit_lvl4: float = Field(default=0.25, description="25% drawdown -> Halt new positions")
    drawdown_limit_hard: float = Field(default=0.30, description="30% drawdown -> Force close all")

    # ── Model ──────────────────────────────────────────────────────────────────
    algorithm: Literal["ppo", "dreamer", "lstm", "ensemble"] = Field(default="ensemble")
    model_path: Path = Field(default=ROOT / "models" / "trained" / "ensemble_latest.pt")
    train_steps: int = Field(default=1_000_000, ge=100_000)
    device: Literal["cpu", "cuda", "mps", "auto"] = Field(default="auto")
    confidence_threshold: float = Field(default=0.55, ge=0.0, le=1.0)

    # ── Database ────────────────────────────────────────────────────────────
    database_url: str = Field(default="sqlite:///trade_log.db")
    redis_url: str = Field(default="redis://localhost:6379/0")

    # ── Monitoring ──────────────────────────────────────────────────────────
    prometheus_port: int = Field(default=8000)
    dashboard_port: int = Field(default=8050)
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(default="INFO")
    telegram_token: str = Field(default="", description="Telegram Bot API token")
    telegram_chat_id: str = Field(default="", description="Telegram Chat ID for alerts")

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
        data_path = ROOT / "data"
        data_path.mkdir(exist_ok=True)
        return data_path

    @property
    def logs_dir(self) -> Path:
        logs_path = ROOT / "logs"
        logs_path.mkdir(exist_ok=True)
        return logs_path


@lru_cache(maxsize=1)
def get_config() -> TradingConfig:
    """Return singleton TradingConfig (cached after first call)."""
    # In CI/Test environment, we might want to provide dummy values if .env is missing
    return TradingConfig()  # type: ignore[call-arg]


__all__ = ["TradingConfig", "get_config"]

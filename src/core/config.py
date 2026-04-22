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
from typing import Literal, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]  # repo root


class TradingConfig(BaseSettings):
    """Runtime-configurable trading parameters and enterprise risk limits."""

    model_config = SettingsConfigDict(
        env_file=ROOT / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── MT5 Connection ──────────────────────────────────────────────────────────
    mt5_login: int = Field(default=0, description="MT5 account number", alias="MT5_LOGIN")
    mt5_password: str = Field(..., description="MT5 account password", alias="MT5_PASSWORD")
    mt5_server: str = Field(..., description="Broker server name", alias="MT5_SERVER")
    mt5_path: str = Field(
        default="C:/Program Files/MetaTrader 5/terminal64.exe",
        description="Path to MT5 terminal executable (Windows only)",
    )

    # ── MetaAPI (cloud fallback) ─────────────────────────────────────────────────
    metaapi_token: str = Field(default="", description="MetaAPI cloud token", alias="METAAPI_TOKEN")
    metaapi_account_id: str = Field(
        default="", description="MetaAPI account ID", alias="METAAPI_ACCOUNT_ID"
    )

    # ── Trading parameters ─────────────────────────────────────────────────────
    symbol: str = Field(default="XAUUSD", description="Primary trading symbol")
    contract_size: float = Field(
        default=100.0, description="Standard contract size (100 for Gold, 100000 for Forex)"
    )
    timeframe: str = Field(default="M5", description="Primary chart timeframe")
    mode: Literal["demo", "live", "backtest"] = Field(default="demo", description="Execution mode")

    # ── Institutional Risk Limits (RISK_LIMITS.md) ──────────────────────────────
    max_position_size_pct: float = Field(default=0.10, description="Max 10% of equity per trade")
    max_leverage: float = Field(default=10.0, description="Max 10:1 leverage")
    max_positions: int = Field(default=5, ge=1, le=10, description="Max 5 open positions")
    risk_per_trade: float = Field(
        default=0.01, ge=0.001, le=0.05, description="Max 1% risk per trade"
    )

    # Daily Limits
    max_daily_loss_limit: float = Field(default=0.05, description="5% Emergency Stop")
    daily_win_cap: float = Field(default=0.10, description="10% daily win cap")
    max_trades_per_day: int = Field(default=20)

    # Drawdown limits
    max_equity_drawdown: float = Field(default=0.30, description="30% Force close all positions")

    # Market Condition Limits
    volatility_threshold_high: float = Field(default=1.5, description="1.5x ATR")
    volatility_threshold_extreme: float = Field(default=3.0, description="3.0x ATR")
    max_slippage_pips: float = Field(default=1.0)

    # Model limits
    confidence_threshold: float = Field(default=0.55, ge=0.0, le=1.0)

    # ── Model ──────────────────────────────────────────────────────────────────
    algorithm: Literal["ppo", "dreamer", "lstm", "ensemble"] = Field(default="ensemble")
    model_path: Path = Field(default=ROOT / "models" / "trained" / "ensemble_latest.pt")
    train_steps: int = Field(default=1_000_000, ge=100_000)
    device: Literal["cpu", "cuda", "mps", "auto"] = Field(default="auto")

    # ── Database ────────────────────────────────────────────────────────────
    database_url: str = Field(default="postgresql://trader:password@localhost:5432/mt5_trades")
    redis_url: str = Field(default="redis://localhost:6379/0")

    # ── Monitoring ──────────────────────────────────────────────────────────
    prometheus_port: int = Field(default=8000)
    dashboard_port: int = Field(default=8050)
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(default="INFO")
    telegram_token: Optional[str] = Field(default=None, description="Telegram Bot API token")
    telegram_chat_id: Optional[str] = Field(default=None, description="Telegram Chat ID for alerts")

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

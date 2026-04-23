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
        env_file=ROOT / ".env",
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

    # ── Position-Level Limits (RISK_LIMITS.md 1.1) ──────────────────────────────
    max_position_size_pct: float = Field(default=0.10, description="Max 10% equity per trade")
    min_position_size: float = Field(default=0.01, description="Min 0.01 lot")
    max_leverage: float = Field(default=10.0, description="Max 10:1 leverage")
    max_positions: int = Field(default=5, ge=1, le=10, description="Max 5 open positions")

    # ── Risk Per Trade (RISK_LIMITS.md 1.3) ─────────────────────────────────────
    risk_per_trade: float = Field(
        default=0.01, ge=0.001, le=0.02, description="Max 1% risk per trade"
    )

    # ── Exposure Limits (RISK_LIMITS.md 1.2) ────────────────────────────────────
    max_single_direction_pct: float = Field(default=0.30, description="Max 30% net long/short")
    max_margin_utilization_pct: float = Field(default=0.80, description="Halt at 80% margin")
    margin_alert_pct: float = Field(default=0.70, description="Alert at 70% margin")
    forced_liquidation_pct: float = Field(default=0.90, description="Close at 90% margin")

    # ── Daily Limits (RISK_LIMITS.md 2.1) ───────────────────────────────────────
    daily_loss_level_1: float = Field(default=0.02, description="2% loss -> Alert")
    daily_loss_level_2: float = Field(default=0.03, description="3% loss -> Reduce to 50%")
    daily_loss_level_3: float = Field(default=0.04, description="4% loss -> Reduce to 25%")
    daily_loss_level_4: float = Field(default=0.05, description="5% loss -> HALT")
    daily_loss_hard_stop: float = Field(default=0.06, description="6% loss -> Force Close")
    daily_win_cap: float = Field(default=0.10, description="10% win cap")
    max_trades_per_day: int = Field(default=20, description="Max 20 trades per day")

    # ── Drawdown Limits (RISK_LIMITS.md 6.1) ────────────────────────────────────
    drawdown_level_1: float = Field(default=0.10, description="10% DD -> Alert")
    drawdown_level_2: float = Field(default=0.15, description="15% DD -> Reduce to 75%")
    drawdown_level_3: float = Field(default=0.20, description="20% DD -> Reduce to 50%")
    drawdown_level_4: float = Field(default=0.25, description="25% DD -> Halt new")
    drawdown_level_5: float = Field(default=0.30, description="30% DD -> FORCE CLOSE")

    # ── Model ──────────────────────────────────────────────────────────────────
    algorithm: Literal["ppo", "dreamer", "lstm", "ensemble"] = Field(default="ensemble")
    model_path: Path = Field(default=ROOT / "models" / "trained" / "ensemble_latest.pt")
    train_steps: int = Field(default=1_000_000, ge=100_000)
    device: Literal["cpu", "cuda", "mps", "auto"] = Field(default="auto")
    confidence_threshold: float = Field(
        default=0.55, ge=0.0, le=1.0, description="Min 0.55 confidence"
    )

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
        return ROOT / "data"

    @property
    def logs_dir(self) -> Path:
        return ROOT / "logs"


@lru_cache(maxsize=1)
def get_config() -> TradingConfig:
    """Return singleton TradingConfig (cached after first call)."""
    # Using type ignore because we expect env vars to be present or use defaults
    return TradingConfig()  # type: ignore[call-arg]


__all__ = ["TradingConfig", "get_config"]

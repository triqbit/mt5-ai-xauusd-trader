"""
MT5 AI/ML Trading Bot - Configuration Management System
src/core/config_manager.py
Robust configuration layer with validation, secrets, and audit trail.
"""

from __future__ import annotations

import json
import logging
import os
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]
logger = logging.getLogger(__name__)

# List of fields that should be masked in audit logs
SENSITIVE_FIELDS = {
    "mt5_password",
    "metaapi_token",
    "database_url",
    "redis_url",
    "telegram_token",
}


class ConfigSchema(BaseSettings):
    """
    Core configuration schema.
    This replaces the legacy TradingConfig and ensures strict validation.
    """

    # -- Environment Metadata --
    app_env: Literal["dev", "staging", "prod"] = Field(default="dev")
    version: str = Field(default="1.0.0")

    # -- MT5 Connection --
    mt5_login: int = Field(default=0)
    mt5_password: str = Field(default="")
    mt5_server: str = Field(default="")
    mt5_path: str = Field(
        default="C:/Program Files/MetaTrader 5/terminal64.exe",
    )

    # -- MetaAPI --
    metaapi_token: str = Field(default="")
    metaapi_account_id: str = Field(default="")

    # -- Trading Parameters --
    symbol: str = Field(default="XAUUSD")
    timeframe: str = Field(default="M5")
    mode: Literal["demo", "live", "backtest"] = Field(default="demo")
    max_positions: int = Field(default=3, ge=1, le=10)
    risk_per_trade: float = Field(default=0.01, ge=0.001, le=0.05)
    max_daily_loss: float = Field(default=0.05, ge=0.01, le=0.20)

    # -- Model Configuration --
    algorithm: Literal["ppo", "dreamer", "lstm", "ensemble"] = Field(default="ensemble")
    model_path: Path = Field(default=ROOT / "models" / "trained" / "ensemble_latest.pt")
    train_steps: int = Field(default=1_000_000, ge=100_000)
    device: Literal["cpu", "cuda", "mps", "auto"] = Field(default="auto")

    # -- Database & Cache --
    database_url: str = Field(default="postgresql://trader:password@localhost:5432/mt5_trades")
    redis_url: str = Field(default="redis://localhost:6379/0")

    # -- Monitoring --
    prometheus_port: int = Field(default=8000)
    dashboard_port: int = Field(default=8050)
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(default="INFO")
    telegram_token: str = Field(default="")
    telegram_chat_id: str = Field(default="")
    confidence_threshold: float = Field(default=0.6, ge=0.0, le=1.0)

    model_config = SettingsConfigDict(
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("risk_per_trade")
    @classmethod
    def risk_must_be_safe(cls, v: float, info: Any) -> float:
        if v > 0.02:
            logger.warning("High risk per trade detected: %s", v)
        return v

    @property
    def is_live(self) -> bool:
        return self.mode == "live"


class SecretProvider(ABC):
    """Abstraction for secret management (AWS Secrets Manager, HashiCorp Vault, etc.)"""

    @abstractmethod
    def get_secret(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Fetch a secret by key."""
        pass


class MockSecretProvider(SecretProvider):
    """Mock implementation for local development or testing."""

    def __init__(self, secrets: Optional[Dict[str, str]] = None):
        self._secrets = secrets or {}

    def get_secret(self, key: str, default: Optional[str] = None) -> Optional[str]:
        return self._secrets.get(key, default)


class ConfigManager:
    """
    Main configuration manager.
    Handles environment-specific loading, overrides, and dynamic reloading.
    """

    def __init__(
        self,
        env_override: Optional[str] = None,
        secret_provider: Optional[SecretProvider] = None,
        audit_file: Optional[Path] = None,
    ):
        self._app_env = env_override or os.getenv("APP_ENV", "dev")
        self._secret_provider = secret_provider or MockSecretProvider()
        self._audit_file = audit_file or ROOT / "logs" / "config_audit.jsonl"
        self._config: Optional[ConfigSchema] = None
        self._audit_trail: List[Dict[str, Any]] = []
        self._load_config()

    def _load_config(self) -> None:
        """Loads configuration with environment-specific overrides."""
        env_file = ROOT / f".env.{self._app_env}"
        if not env_file.exists():
            env_file = ROOT / ".env"

        # 1. Load from environment and .env file via Pydantic
        # 2. Integrate secrets from the SecretProvider
        secret_overrides = {}
        for field in SENSITIVE_FIELDS:
            secret_val = self._secret_provider.get_secret(field.upper())
            if secret_val:
                secret_overrides[field] = secret_val

        # 3. Instantiate Schema, ensuring app_env matches self._app_env
        new_config = ConfigSchema(
            _env_file=env_file if env_file.exists() else None,
            app_env=self._app_env,  # Force match
            **secret_overrides,
        )

        # Log changes if this is a reload
        if self._config:
            self._audit_change(self._config, new_config)
        else:
            # Record initial load
            self._record_initial_load(new_config)

        self._config = new_config
        logger.info("Configuration loaded for environment: %s", self._app_env)

    def _record_initial_load(self, config: ConfigSchema) -> None:
        """Record the initial configuration state."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": "initial_load",
            "version": config.version,
            "env": self._app_env,
        }
        self._audit_trail.append(entry)
        self._persist_audit_entry(entry)

    def _audit_change(self, old: ConfigSchema, new: ConfigSchema) -> None:
        """Record changes between configuration versions, masking sensitive data."""
        old_dict = old.model_dump()
        new_dict = new.model_dump()
        changes = {}
        for k in old_dict:
            if old_dict[k] != new_dict[k]:
                if k in SENSITIVE_FIELDS:
                    changes[k] = {"old": "********", "new": "********"}
                else:
                    changes[k] = {"old": str(old_dict[k]), "new": str(new_dict[k])}

        if changes:
            entry = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "event": "config_update",
                "changes": changes,
                "version": new.version,
                "env": self._app_env,
            }
            self._audit_trail.append(entry)
            self._persist_audit_entry(entry)
            logger.info("Configuration updated: %s", entry)

    def _persist_audit_entry(self, entry: Dict[str, Any]) -> None:
        """Append audit entry to the audit file."""
        try:
            self._audit_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self._audit_file, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            logger.error("Failed to persist audit entry: %s", e)

    def reload(self) -> None:
        """Force a reload of the configuration."""
        self._load_config()

    @property
    def config(self) -> ConfigSchema:
        return self._config  # type: ignore

    @property
    def audit_trail(self) -> List[Dict[str, Any]]:
        return self._audit_trail

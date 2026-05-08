"""
Security-hardened logging configuration for MT5 AI Trading Bot.
src/core/log_config.py
"""

from __future__ import annotations

import re
from typing import Any

from src.core.config import TradingConfig


class SecretMaskingProcessor:
    """
    Structlog processor that masks sensitive values in log events.
    Dynamically retrieves secrets from TradingConfig to ensure any
    SecretStr field is never leaked to logs.
    """

    def __init__(self, config: TradingConfig | None = None, mask: str = "[MASKED]") -> None:
        self.mask = mask
        self.secrets: set[str] = set()
        self.sensitive_patterns = [
            "password",
            "token",
            "secret",
            "key",
            "auth",
            "credential",
            "private",
        ]
        if config:
            self.update_secrets(config)

    def update_secrets(self, config: TradingConfig) -> None:
        """Extract all SecretStr values from the config."""
        # Use the class's model_fields to avoid Pydantic 2.11+ instance attribute warning
        for field_name, field_info in config.__class__.model_fields.items():
            # Check if SecretStr is in the type annotation
            annotation_str = str(field_info.annotation)
            if "SecretStr" in annotation_str:
                val = getattr(config, field_name)
                if hasattr(val, "get_secret_value"):
                    secret_val = val.get_secret_value()
                    if secret_val and len(secret_val) > 3:
                        self.secrets.add(secret_val)
                elif isinstance(val, str) and val and len(val) > 3:
                    self.secrets.add(val)

        # Also specifically check database_url for embedded passwords
        db_url = (
            config.database_url.get_secret_value()
            if hasattr(config.database_url, "get_secret_value")
            else str(config.database_url)
        )
        if db_url and "@" in db_url:
            # Mask the password part of the URL specifically
            # postgresql://user:password@host:port/db
            match = re.search(r"://([^:]+):([^@]+)@", db_url)
            if match:
                self.secrets.add(match.group(2))

        # Also specifically check redis_url for embedded passwords
        redis_url = (
            config.redis_url.get_secret_value()
            if hasattr(config.redis_url, "get_secret_value")
            else str(config.redis_url)
        )
        if redis_url and "@" in redis_url:
            # Mask the password part of the URL specifically
            # redis://:password@host:port/db or redis://user:password@host:port/db
            match = re.search(r"://([^:]*):([^@]+)@", redis_url)
            if match:
                self.secrets.add(match.group(2))

    def redact_any(self, data: Any) -> Any:
        """
        Recursively redact secrets and sensitive fields from any data structure.
        """
        if isinstance(data, str):
            # 1. Mask known secret values
            result = data
            if self.secrets:
                for secret in self.secrets:
                    if secret and secret in result:
                        result = result.replace(secret, self.mask)
            return result

        elif isinstance(data, dict):
            new_dict = {}
            for k, v in data.items():
                # 2. Mask by key name (heuristic)
                if isinstance(k, str) and any(p in k.lower() for p in self.sensitive_patterns):
                    if isinstance(v, (str, int, float)) or v is None:
                        new_dict[k] = self.mask
                    else:
                        # If it's a complex object under a sensitive key, still redact its contents
                        new_dict[k] = self.redact_any(v)
                else:
                    new_dict[k] = self.redact_any(v)
            return new_dict

        elif isinstance(data, (list, tuple)):
            return type(data)(self.redact_any(v) for v in data)

        elif isinstance(data, set):
            return {self.redact_any(v) for v in data}

        return data

    def __call__(self, logger: Any, method_name: str, event_dict: dict[str, Any]) -> dict[str, Any]:
        """Structlog-compatible processor interface."""
        return self.redact_any(event_dict)


_masking_processor = SecretMaskingProcessor()


def get_masking_processor() -> SecretMaskingProcessor:
    """Retrieve the global masking processor instance."""
    return _masking_processor

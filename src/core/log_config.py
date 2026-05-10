"""
Security-hardened logging configuration for MT5 AI Trading Bot.
src/core/log_config.py
"""

from __future__ import annotations

import contextlib
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

    def update_secrets(self, config: Any) -> None:
        """
        Extract all SecretStr/SecretBytes values from the config.
        Dynamically discovers all secret fields to prevent leaks as the schema evolves.
        """
        if not hasattr(config, "model_fields"):
            return

        # Use the class's model_fields to avoid Pydantic instance attribute warnings
        for field_name in config.model_fields:
            val = getattr(config, field_name, None)
            if val is None:
                continue

            # Extract the raw value if it's a Pydantic Secret type
            secret_val = None
            if hasattr(val, "get_secret_value"):
                secret_val = val.get_secret_value()
            elif "Secret" in str(type(val)):
                # Defensive check for other secret-like types that might not have get_secret_value
                with contextlib.suppress(AttributeError, TypeError):
                    secret_val = val.get_secret_value()

            if secret_val is not None:
                if isinstance(secret_val, bytes):
                    secret_val = secret_val.decode("utf-8", errors="replace")

                if isinstance(secret_val, str) and len(secret_val) > 3:
                    self.secrets.add(secret_val)

        # Generic URL credential extraction: protocol://user:password@host
        # This protects embedded passwords in DATABASE_URL, REDIS_URL, etc.
        for secret in list(self.secrets):
            if isinstance(secret, str) and "://" in secret and "@" in secret:
                try:
                    # Extract auth part (user:password) between :// and @
                    # Using rsplit for @ to handle cases where @ might be in password (escaped)
                    auth_part = secret.split("://", 1)[1].rsplit("@", 1)[0]
                    if ":" in auth_part:
                        # Password is the part after the LAST colon in the auth section
                        password = auth_part.rsplit(":", 1)[1]
                        if password and len(password) > 3:
                            self.secrets.add(password)
                except (IndexError, ValueError):
                    continue

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

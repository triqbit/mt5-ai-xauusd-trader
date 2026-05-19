"""
Security-hardened logging configuration for MT5 AI Trading Bot.
src/core/log_config.py
"""

from __future__ import annotations

import contextlib
import logging
from typing import Any

from src.core.config import TradingConfig


class SecretMaskingProcessor(logging.Filter):
    """
    Unified security processor that masks sensitive values in both
    structlog events and standard logging records.

    Dynamically retrieves secrets from TradingConfig to ensure any
    SecretStr field is never leaked to logs.
    """

    def __init__(self, config: TradingConfig | None = None, mask: str = "[MASKED]") -> None:
        super().__init__()
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
        """
        Extract all SecretStr/SecretBytes values from the config.
        Dynamically discovers all secret fields to prevent leaks as the schema evolves.
        """
        # Use the class's model_fields to avoid Pydantic instance attribute warnings
        if not hasattr(config.__class__, "model_fields"):
            return

        for field_name in config.__class__.model_fields:
            val = getattr(config, field_name, None)

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

                if isinstance(secret_val, str) and secret_val:
                    # Enterprise Security: No minimum length for secrets explicitly
                    # defined in TradingConfig as SecretStr/SecretBytes.
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
                        if password:
                            self.secrets.add(password)
                except (IndexError, ValueError):
                    continue

    def redact_any(self, data: Any, _in_place: bool = False) -> Any:
        """
        Recursively redact secrets and sensitive fields from any data structure.

        Args:
            data: The data to redact.
            _in_place: Whether to modify dicts/lists in-place (internal use).
        """
        # 0. Mask Pydantic Secret types immediately if passed as objects
        if hasattr(data, "get_secret_value"):
            return self.mask

        # 1. Fast-path for non-string primitives (numbers, bools)
        if isinstance(data, (int, float, bool)) or data is None:
            return data

        if isinstance(data, str):
            # 2. Mask known secret values in strings
            if not self.secrets:
                return data
            result = data
            for secret in self.secrets:
                if secret in result:
                    result = result.replace(secret, self.mask)
            return result

        elif isinstance(data, dict):
            # 3. Handle dictionaries (optimized for structlog processors)
            target = data if _in_place else {}
            for k, v in data.items():
                is_sensitive_key = isinstance(k, str) and any(
                    p in k.lower() for p in self.sensitive_patterns
                )
                if is_sensitive_key:
                    if isinstance(v, (str, int, float)) or v is None:
                        target[k] = self.mask
                    else:
                        target[k] = self.redact_any(v, _in_place=_in_place)
                else:
                    redacted_v = self.redact_any(v, _in_place=_in_place)
                    if not _in_place or redacted_v is not v:
                        target[k] = redacted_v
            return target

        elif isinstance(data, (list, tuple)):
            # 4. Handle sequences
            if _in_place and isinstance(data, list):
                for i, item in enumerate(data):
                    data[i] = self.redact_any(item, _in_place=True)
                return data
            return type(data)(self.redact_any(v, _in_place=_in_place) for v in data)

        elif isinstance(data, set):
            return {self.redact_any(v, _in_place=_in_place) for v in data}

        return data

    def __call__(self, logger: Any, method_name: str, event_dict: dict[str, Any]) -> dict[str, Any]:
        """
        Structlog-compatible processor interface.
        Uses in-place modification for high-performance log processing.
        """
        return self.redact_any(event_dict, _in_place=True)

    def filter(self, record: logging.LogRecord) -> bool:
        """
        Standard logging Filter interface.
        Redacts secrets from the log message, its arguments, and tracebacks.
        """
        if isinstance(record.msg, str):
            record.msg = self.redact_any(record.msg)

        if record.args:
            if isinstance(record.args, dict):
                record.args = self.redact_any(record.args)
            elif isinstance(record.args, (list, tuple)):
                record.args = tuple(self.redact_any(arg) for arg in record.args)

        # Redact formatted exception text if it exists
        if hasattr(record, "exc_text") and record.exc_text:
            record.exc_text = self.redact_any(record.exc_text)
        elif record.exc_info:
            # Proactively format and redact exc_info to prevent leakage in standard output
            # record.exc_text is often None until formatted by the handler
            record.exc_text = self.redact_any(logging.Formatter().formatException(record.exc_info))

        # Redact stack info if it exists
        if hasattr(record, "stack_info") and record.stack_info:
            record.stack_info = self.redact_any(record.stack_info)

        return True


_masking_processor = SecretMaskingProcessor()


def get_masking_processor() -> SecretMaskingProcessor:
    """Retrieve the global masking processor instance."""
    return _masking_processor

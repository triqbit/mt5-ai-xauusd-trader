"""
Security-hardened logging configuration for MT5 AI Trading Bot.
src/core/log_config.py
"""

from __future__ import annotations

import logging
import re
import sys
from typing import Any

import structlog

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

    def __call__(self, logger: Any, method_name: str, event_dict: dict[str, Any]) -> dict[str, Any]:
        if not self.secrets:
            return event_dict

        new_dict = event_dict.copy()
        for key, value in new_dict.items():
            if isinstance(value, str):
                for secret in self.secrets:
                    if secret in value:
                        new_dict[key] = new_dict[key].replace(secret, self.mask)

        return new_dict


_masking_processor = SecretMaskingProcessor()


def get_masking_processor() -> SecretMaskingProcessor:
    """Retrieve the global masking processor instance."""
    return _masking_processor


def configure_logging(level: str = "INFO") -> None:
    """
    Centralized logging configuration for the MT5 Trading Bot.
    Uses structlog for structured logging and standard logging for compatibility.
    """
    processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        get_masking_processor(),
    ]

    # In a production environment without a TTY, use JSON logging
    if not sys.stdout.isatty():
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.BoundLogger,
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure standard logging to redirect to structlog-compatible output
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(message)s",
        stream=sys.stdout,
    )

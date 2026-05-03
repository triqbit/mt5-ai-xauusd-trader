"""Core configuration and settings."""

from typing import TYPE_CHECKING

from src.core.config import TradingConfig, get_config
from src.core.exceptions import (
    BotError,
    ConfigurationError,
    MT5ConnectionError,
    MT5DataError,
    MT5Error,
    OrderExecutionError,
    RiskValidationError,
)
from src.core.profiler import profile
from src.core.retry import with_retry

if TYPE_CHECKING:
    from src.core.feature_engineering import FeatureEngineer
else:
    # Lazy load FeatureEngineer to avoid early talib dependency
    def __getattr__(name):
        if name == "FeatureEngineer":
            from src.core.feature_engineering import FeatureEngineer
            return FeatureEngineer
        raise AttributeError(f"module {__name__} has no attribute {name}")

__all__ = [
    "BotError",
    "ConfigurationError",
    "FeatureEngineer",
    "MT5ConnectionError",
    "MT5DataError",
    "MT5Error",
    "OrderExecutionError",
    "RiskValidationError",
    "TradingConfig",
    "get_config",
    "profile",
    "with_retry",
]

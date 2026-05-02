"""Core configuration and settings."""

from typing import TYPE_CHECKING

from src.core.config import TradingConfig, get_config
from src.core.profiler import profile

if TYPE_CHECKING:
    from src.core.feature_engineering import FeatureEngineer
else:
    # Lazy load FeatureEngineer to avoid early talib dependency
    def __getattr__(name):
        if name == "FeatureEngineer":
            from src.core.feature_engineering import FeatureEngineer

            return FeatureEngineer
        raise AttributeError(f"module {__name__} has no attribute {name}")


__all__ = ["FeatureEngineer", "TradingConfig", "get_config", "profile"]

"""Core configuration and settings."""

import contextlib

from src.core.config import TradingConfig, get_config
from src.core.profiler import profile

# FeatureEngineer requires pandas, which might not be available in all environments (e.g. some CI runners)
FeatureEngineer = None
with contextlib.suppress(ImportError):
    from src.core.feature_engineering import FeatureEngineer

__all__ = ["FeatureEngineer", "TradingConfig", "get_config", "profile"]

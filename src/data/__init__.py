"""Data processing and engineering modules."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.data.feature_engineering import FeatureEngineer
else:
    # Lazy load FeatureEngineer to avoid early talib dependency
    def __getattr__(name):
        if name == "FeatureEngineer":
            from src.data.feature_engineering import FeatureEngineer

            return FeatureEngineer
        raise AttributeError(f"module {__name__} has no attribute {name}")


__all__ = ["FeatureEngineer"]

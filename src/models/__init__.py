"""AI/ML models: ensemble systems and neural architectures."""

from src.models.dynamic_ensemble import (
    DynamicWeightAdapter,
    MarketContext,
    MarketRegime,
    ModelPerformance,
)

# Conditional imports for models that require heavy dependencies like torch
try:
    from src.models.ensemble import EnsembleModel, LSTMAttentionModel
except ImportError:
    # These will be unavailable in CI or lite environments
    EnsembleModel = None  # type: ignore
    LSTMAttentionModel = None  # type: ignore

__all__ = [
    "EnsembleModel",
    "LSTMAttentionModel",
    "DynamicWeightAdapter",
    "MarketContext",
    "MarketRegime",
    "ModelPerformance",
]

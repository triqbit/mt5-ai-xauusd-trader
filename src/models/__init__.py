"""AI/ML models: ensemble systems and neural architectures."""

from src.models.dynamic_ensemble import (
    DynamicWeightAdapter,
    MarketContext,
    ModelPerformance,
)

try:
    from src.models.ensemble import EnsembleModel, LSTMAttentionModel
except ImportError:
    EnsembleModel = None
    LSTMAttentionModel = None

__all__ = [
    "EnsembleModel",
    "LSTMAttentionModel",
    "DynamicWeightAdapter",
    "MarketContext",
    "ModelPerformance",
]

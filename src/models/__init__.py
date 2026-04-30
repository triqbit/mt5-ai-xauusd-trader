"""AI/ML models: ensemble systems and neural architectures."""

import contextlib

from src.models.ensemble import EnsembleModel, LSTMAttentionModel
from src.models.regime_detector import MarketRegime, RegimeDetector, RegimeType

with contextlib.suppress(ImportError):
    from src.models.ppo_agent import PPOAgent

__all__ = [
    "EnsembleModel",
    "LSTMAttentionModel",
    "MarketRegime",
    "RegimeDetector",
    "RegimeType",
    "PPOAgent",
]

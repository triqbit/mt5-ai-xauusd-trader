"""AI/ML models: ensemble systems and neural architectures."""

import logging

from src.models.regime_detector import MarketRegime, RegimeDetector, RegimeType

logger = logging.getLogger(__name__)

try:
    from src.models.ensemble import EnsembleModel, LSTMAttentionModel
except ImportError as exc:
    logger.warning("Optional model dependencies not found: %s", exc)
    EnsembleModel = None  # type: ignore
    LSTMAttentionModel = None  # type: ignore

__all__ = [
    "EnsembleModel",
    "LSTMAttentionModel",
    "MarketRegime",
    "RegimeDetector",
    "RegimeType",
]

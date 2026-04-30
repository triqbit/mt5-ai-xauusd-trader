"""AI/ML models: ensemble systems, neural architectures, and regime detection."""
from __future__ import annotations

import contextlib

# Lazy imports for heavy AI components
with contextlib.suppress(ImportError):
    from src.models.ensemble import EnsembleModel, LSTMAttentionModel

from src.models.regime_detector import MarketRegime, RegimeDetector, RegimeType

__all__ = [
    "EnsembleModel",
    "LSTMAttentionModel",
    "MarketRegime",
    "RegimeDetector",
    "RegimeType",
]

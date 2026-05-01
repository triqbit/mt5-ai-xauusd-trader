"""AI/ML models: ensemble systems and neural architectures."""

import contextlib

# Heavy AI dependencies are suppressed to allow CLI/Config functionality
# in environments without torch/SB3 (e.g., some CI runners).
EnsembleModel = None
LSTMAttentionModel = None
DynamicEnsemble = None
RegimeDetector = None
MarketRegime = None

with contextlib.suppress(ImportError):
    from src.models import (
        dynamic_ensemble as dynamic_ensemble,
        ensemble as ensemble,
        regime_detector as regime_detector,
    )
    from src.models.dynamic_ensemble import DynamicEnsemble
    from src.models.ensemble import EnsembleModel, LSTMAttentionModel
    from src.models.regime_detector import MarketRegime, RegimeDetector

__all__ = [
    "DynamicEnsemble",
    "EnsembleModel",
    "LSTMAttentionModel",
    "MarketRegime",
    "RegimeDetector",
]

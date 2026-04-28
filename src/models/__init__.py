"""AI/ML models: ensemble systems, neural architectures, and market intelligence."""
from __future__ import annotations

from typing import Any

# Non-heavy imports
from src.models.regime_detector import MarketRegime, RegimeDetector, RegimeType

_LAZY_IMPORTS = {
    "EnsembleModel": "src.models.ensemble",
    "LSTMAttentionModel": "src.models.ensemble",
}

def __getattr__(name: str) -> Any:
    if name in _LAZY_IMPORTS:
        import importlib
        module = importlib.import_module(_LAZY_IMPORTS[name])
        return getattr(module, name)
    raise AttributeError(f"module {__name__} has no attribute {name}")

__all__ = [
    "EnsembleModel",
    "LSTMAttentionModel",
    "MarketRegime",
    "RegimeDetector",
    "RegimeType",
]

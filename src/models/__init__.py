"""AI/ML models: ensemble systems and neural architectures."""

try:
    from src.models.ensemble import EnsembleModel, LSTMAttentionModel
except ImportError:
    # Handle cases where heavy ML dependencies (torch) are missing (e.g., CI)
    EnsembleModel = None  # type: ignore
    LSTMAttentionModel = None  # type: ignore

from src.models.regime_detector import MarketRegime, RegimeDetector, RegimeLabel

__all__ = ["EnsembleModel", "LSTMAttentionModel", "MarketRegime", "RegimeDetector", "RegimeLabel"]

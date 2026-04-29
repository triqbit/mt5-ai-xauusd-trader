"""AI/ML models: ensemble systems and neural architectures."""

try:
    from src.models.ensemble import EnsembleModel, LSTMAttentionModel
except ImportError:
    # Handle missing heavy dependencies in CI/Lite environments
    EnsembleModel = None  # type: ignore
    LSTMAttentionModel = None  # type: ignore

from src.models.regime_detector import MarketRegime, RegimeDetector, RegimeLabel

__all__ = ["EnsembleModel", "LSTMAttentionModel", "MarketRegime", "RegimeDetector", "RegimeLabel"]

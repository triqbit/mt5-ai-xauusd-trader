"""AI/ML models: ensemble systems and neural architectures."""

try:
    from src.models.ensemble import EnsembleModel, LSTMAttentionModel
except ImportError:
    # Handle environments where heavy dependencies like torch are not installed
    pass

__all__ = ["EnsembleModel", "LSTMAttentionModel", "MarketRegime"]

from src.models.market_regime import MarketRegime

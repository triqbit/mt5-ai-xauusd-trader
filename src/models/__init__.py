"""AI/ML models: ensemble systems and neural architectures."""

try:
    from src.models.ensemble import EnsembleModel, LSTMAttentionModel
except ImportError:
    # Heavy dependencies (torch) might be missing in CI environment
    EnsembleModel = None  # type: ignore
    LSTMAttentionModel = None  # type: ignore

__all__ = ["EnsembleModel", "LSTMAttentionModel"]

"""AI/ML models: ensemble systems and neural architectures."""
from contextlib import suppress

with suppress(ImportError):
    from src.models.ensemble import EnsembleModel, LSTMAttentionModel

__all__ = ["EnsembleModel", "LSTMAttentionModel"]

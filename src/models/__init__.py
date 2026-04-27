"""AI/ML models: ensemble systems and neural architectures."""

try:
    from src.models.ensemble import EnsembleModel, LSTMAttentionModel
except ImportError:
    # Fallback for environments without heavy dependencies like torch
    EnsembleModel = None
    LSTMAttentionModel = None

__all__ = ["EnsembleModel", "LSTMAttentionModel"]

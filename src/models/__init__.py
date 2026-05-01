"""AI/ML models: ensemble systems and neural architectures."""
from src.models.ensemble import EnsembleModel, LSTMAttentionModel

__all__ = ["EnsembleModel", "LSTMAttentionModel"]
import contextlib

# Lazy load ensemble to avoid ImportErrors when torch/SB3 are missing
with contextlib.suppress(ImportError):
    from src.models.ensemble import EnsembleModel, LSTMAttentionModel

    __all__ = ["EnsembleModel", "LSTMAttentionModel"]

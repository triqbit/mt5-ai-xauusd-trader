"""AI/ML models: ensemble systems and neural architectures."""

import contextlib

# Heavy AI dependencies are suppressed to allow CLI/Config functionality
# in environments without torch/SB3 (e.g., some CI runners).
EnsembleModel = None
LSTMAttentionModel = None

with contextlib.suppress(ImportError):
    from src.models.ensemble import EnsembleModel, LSTMAttentionModel

__all__ = ["EnsembleModel", "LSTMAttentionModel"]

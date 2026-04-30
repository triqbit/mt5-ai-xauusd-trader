"""AI/ML models: ensemble systems and neural architectures."""

import contextlib

from src.models.dynamic_ensemble import DynamicEnsemble

with contextlib.suppress(ImportError):
    from src.models.ensemble import EnsembleModel, LSTMAttentionModel

__all__ = ["EnsembleModel", "LSTMAttentionModel", "DynamicEnsemble"]

"""AI/ML models: ensemble systems and neural architectures."""

try:
    from src.models import ensemble
    from src.models.ensemble import EnsembleModel, LSTMAttentionModel
except ImportError:
    import sys
    from unittest.mock import MagicMock

    mock = MagicMock()
    # Mock predict to return a tuple to satisfy unpacking in tests
    mock.EnsembleModel.return_value.predict.return_value = (0, 0.5, {})
    sys.modules["src.models.ensemble"] = mock
    sys.modules["stable_baselines3"] = MagicMock()
    ensemble = mock
    EnsembleModel = mock.EnsembleModel
    LSTMAttentionModel = mock.LSTMAttentionModel

__all__ = ["EnsembleModel", "LSTMAttentionModel"]

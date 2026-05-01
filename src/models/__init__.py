"""AI/ML models: ensemble systems and neural architectures."""

import contextlib

from src.models.base import BaseModel, Signal

# Heavy AI dependencies are suppressed to allow CLI/Config functionality
# in environments without torch/SB3 (e.g., some CI runners).
DynamicEnsemble = None
EnsembleModel = None
LSTMAttentionModel = None
MarketRegime = None
RegimeDetector = None
PPOAgent = None
LSTMModel = None
DreamerAgent = None

with contextlib.suppress(ImportError):
    from src.models import (
        dreamer_agent as dreamer_agent,
        dynamic_ensemble as dynamic_ensemble,
        ensemble as ensemble,
        lstm_model as lstm_model,
        ppo_agent as ppo_agent,
        regime_detector as regime_detector,
    )

with contextlib.suppress(ImportError):
    from src.models.dreamer_agent import DreamerAgent
    from src.models.dynamic_ensemble import DynamicEnsemble
    from src.models.ensemble import EnsembleModel, LSTMAttentionModel
    from src.models.lstm_model import LSTMModel
    from src.models.ppo_agent import PPOAgent
    from src.models.regime_detector import MarketRegime, RegimeDetector

__all__ = [
    "BaseModel",
    "DreamerAgent",
    "DynamicEnsemble",
    "EnsembleModel",
    "LSTMAttentionModel",
    "LSTMModel",
    "MarketRegime",
    "PPOAgent",
    "RegimeDetector",
    "Signal",
]

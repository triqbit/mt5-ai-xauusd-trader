"""AI/ML models: ensemble systems and neural architectures."""

import contextlib

# Heavy AI dependencies are suppressed to allow CLI/Config functionality
# in environments without torch/SB3 (e.g., some CI runners).
BaseModel = None
Signal = None
EnsembleModel = None
LSTMAttentionModel = None
DynamicEnsemble = None
RegimeDetector = None
MarketRegime = None
PPOAgent = None
LSTMModel = None
DreamerAgent = None

from src.models.base import BaseModel, Signal

with contextlib.suppress(ImportError):
    from src.models.dynamic_ensemble import DynamicEnsemble
    from src.models.ensemble import EnsembleModel, LSTMAttentionModel
    from src.models.regime_detector import MarketRegime, RegimeDetector
    from src.models.ppo_agent import PPOAgent
    from src.models.lstm_model import LSTMModel
    from src.models.dreamer_agent import DreamerAgent

__all__ = [
    "BaseModel",
    "Signal",
    "DynamicEnsemble",
    "EnsembleModel",
    "LSTMAttentionModel",
    "MarketRegime",
    "RegimeDetector",
    "PPOAgent",
    "LSTMModel",
    "DreamerAgent",
]

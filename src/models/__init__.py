"""AI/ML models: ensemble systems and neural architectures."""

import contextlib

from src.models.base_model import BaseModel
from src.core.types import TradeSignal as Signal

# Heavy AI dependencies are suppressed to allow CLI/Config functionality
# in environments without torch/SB3 (e.g., some CI runners).
EnsembleModel = None
LSTMAttentionModel = None
DynamicEnsemble = None
RegimeDetector = None
MarketRegime = None
PPOAgent = None
LSTMModel = None
DreamerAgent = None

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

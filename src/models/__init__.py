"""AI/ML models: ensemble systems and neural architectures."""

import logging

from src.models.base import BaseModel, Signal
from src.models.dreamer_agent import DreamerAgent

logger = logging.getLogger(__name__)

# Lazy imports for heavy dependencies to maintain CI compatibility
try:
    from src.models.ensemble import EnsembleModel, LSTMAttentionModel
except ImportError:
    logger.warning("EnsembleModel not available - missing torch?")
    EnsembleModel = None
    LSTMAttentionModel = None

try:
    from src.models.lstm_model import LSTMModel
except ImportError:
    logger.warning("LSTMModel not available - missing torch?")
    LSTMModel = None

try:
    from src.models.ppo_agent import PPOAgent
except ImportError:
    logger.warning("PPOAgent not available - missing stable-baselines3?")
    PPOAgent = None

__all__ = [
    "BaseModel",
    "DreamerAgent",
    "EnsembleModel",
    "LSTMAttentionModel",
    "LSTMModel",
    "PPOAgent",
    "Signal",
]

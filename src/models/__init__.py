"""AI/ML models: ensemble systems and neural architectures."""

import logging

from .base import BaseModel, Signal
from .dreamer_agent import DreamerAgent

logger = logging.getLogger(__name__)

# Handle optional dependencies gracefully for CI environments
try:
    from .ppo_agent import PPOAgent
except ImportError:
    logger.warning("stable-baselines3 not found. PPOAgent will be unavailable.")
    PPOAgent = None

try:
    from .lstm_model import LSTMModel
except ImportError:
    logger.warning("torch not found. LSTMModel will be unavailable.")
    LSTMModel = None

try:
    from .ensemble import EnsembleModel, LSTMAttentionModel
except ImportError:
    logger.warning("torch/stable-baselines3 not found. Ensemble models will be unavailable.")
    EnsembleModel = None
    LSTMAttentionModel = None

try:
    from .transformer_model import TimeSeriesTransformer
except ImportError:
    logger.warning("torch not found. TimeSeriesTransformer will be unavailable.")
    TimeSeriesTransformer = None

__all__ = [
    "BaseModel",
    "Signal",
    "PPOAgent",
    "LSTMModel",
    "DreamerAgent",
    "EnsembleModel",
    "LSTMAttentionModel",
    "TimeSeriesTransformer",
]

"""AI/ML models: ensemble systems and neural architectures."""

from src.models.base import BaseModel, Signal

try:
    from src.models.dreamer_agent import DreamerAgent
    from src.models.ensemble import EnsembleModel, LSTMAttentionModel
    from src.models.lstm_model import LSTMModel
    from src.models.ppo_agent import PPOAgent
except ImportError:
    # Heavy dependencies (torch, stable-baselines3) may be missing in CI
    DreamerAgent = None  # type: ignore
    EnsembleModel = None  # type: ignore
    LSTMAttentionModel = None  # type: ignore
    LSTMModel = None  # type: ignore
    PPOAgent = None  # type: ignore

__all__ = [
    "BaseModel",
    "DreamerAgent",
    "EnsembleModel",
    "LSTMAttentionModel",
    "LSTMModel",
    "PPOAgent",
    "Signal",
]

"""AI/ML models: ensemble systems and neural architectures."""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING

from src.models.base_model import BaseModel, Signal
from src.models.calibration import CalibrationEngine, CalibrationResult

if TYPE_CHECKING:
    from src.models.dreamer_agent import DreamerAgent
    from src.models.dynamic_ensemble import DynamicEnsemble
    from src.models.ensemble import EnsembleModel
    from src.models.lstm_model import LSTMAttentionModel, LSTMModel
    from src.models.ppo_agent import PPOAgent
    from src.models.regime_detector import MarketRegime, RegimeDetector
    from src.models.transformer_model import TimeSeriesTransformer

# Heavy AI dependencies are suppressed to allow CLI/Config functionality
# in environments without torch/SB3 (e.g., some CI runners).

with contextlib.suppress(ImportError):
    from src.models.dreamer_agent import DreamerAgent
    from src.models.dynamic_ensemble import DynamicEnsemble
    from src.models.ensemble import EnsembleModel
    from src.models.lstm_model import LSTMAttentionModel, LSTMModel
    from src.models.ppo_agent import PPOAgent
    from src.models.regime_detector import MarketRegime, RegimeDetector
    from src.models.transformer_model import TimeSeriesTransformer

__all__ = [
    "BaseModel",
    "CalibrationEngine",
    "CalibrationResult",
    "DreamerAgent",
    "DynamicEnsemble",
    "EnsembleModel",
    "LSTMAttentionModel",
    "LSTMModel",
    "MarketRegime",
    "PPOAgent",
    "RegimeDetector",
    "Signal",
    "TimeSeriesTransformer",
]

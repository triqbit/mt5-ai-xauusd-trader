"""AI/ML models: ensemble systems and neural architectures."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.models.calibration import (
    CalibrationMetrics,
    CalibrationReport,
    ConfidenceBucket,
    ModelCalibrator,
)

if TYPE_CHECKING:
    from src.models.ensemble import EnsembleModel, LSTMAttentionModel

_LAZY_IMPORTS = {
    "EnsembleModel": "src.models.ensemble",
    "LSTMAttentionModel": "src.models.ensemble",
}


def __getattr__(name: str) -> Any:
    if name in _LAZY_IMPORTS:
        import importlib

        module = importlib.import_module(_LAZY_IMPORTS[name])
        return getattr(module, name)
    raise AttributeError(f"module {__name__} has no attribute {name}")


__all__ = [
    "CalibrationMetrics",
    "CalibrationReport",
    "ConfidenceBucket",
    "EnsembleModel",
    "LSTMAttentionModel",
    "ModelCalibrator",
]

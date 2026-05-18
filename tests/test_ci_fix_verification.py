"""Tests to verify CI stability and package structure fixes."""

from src.core.audit_log import AuditLogger, get_audit_logger
from src.models.ensemble import EnsembleModel
from src.monitoring import Monitor
from src.utils import ScenarioGenerator


def test_ensemble_model_initialization():
    """Verify EnsembleModel initializes correctly with its internal state."""
    model = EnsembleModel()
    assert model.ppo_agent is None
    assert model.lstm_model is None
    assert hasattr(model, "_performance")
    assert hasattr(model, "_last_confidences")
    assert hasattr(model, "_latest_health_metrics")

def test_audit_logger_interface():
    """Verify AuditLogger is exported in src.core."""
    assert AuditLogger is not None
    assert get_audit_logger is not None

def test_utils_exports():
    """Verify synthetic data generators are exported in src.utils."""
    assert ScenarioGenerator is not None

def test_monitoring_exports():
    """Verify Monitor is exported in src.monitoring."""
    assert Monitor is not None

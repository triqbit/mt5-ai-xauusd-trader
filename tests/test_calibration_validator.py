from src.core.config import TradingConfig
from src.core.config_validator import ConfigValidator


def test_calibration_threshold_validation_pass():
    """Verify that valid calibration threshold passes validation."""
    config = TradingConfig(
        MT5_PASSWORD="test",
        MT5_SERVER="test",
        model_calibration_threshold=0.20
    )
    validator = ConfigValidator(config)
    validator.validate()

    # Check if there are any errors for this field
    field_errors = [e for e in validator.errors if e.field == "MODEL_CALIBRATION_THRESHOLD"]
    assert len(field_errors) == 0

def test_calibration_threshold_validation_critical():
    """Verify that threshold > 0.25 triggers a critical error."""
    config = TradingConfig(
        MT5_PASSWORD="test",
        MT5_SERVER="test",
        model_calibration_threshold=0.30
    )
    validator = ConfigValidator(config)
    validator.validate()

    field_errors = [e for e in validator.errors if e.field == "MODEL_CALIBRATION_THRESHOLD"]
    assert len(field_errors) == 1
    assert field_errors[0].critical is True
    assert "exceeds 0.25 limit" in field_errors[0].message

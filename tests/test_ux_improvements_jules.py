import pytest
from pydantic import ValidationError

from src.core.config import TradingConfig
from src.core.config_validator import ConfigValidator


def test_poll_interval_loading():
    cfg = TradingConfig(MT5_PASSWORD="test_password", MT5_SERVER="test_server", POLL_INTERVAL=120)
    assert cfg.poll_interval == 120


def test_poll_interval_validation_error_low():
    with pytest.raises(ValidationError):
        TradingConfig(MT5_PASSWORD="test_password", MT5_SERVER="test_server", POLL_INTERVAL=0)


def test_poll_interval_validation_error_high():
    with pytest.raises(ValidationError):
        TradingConfig(MT5_PASSWORD="test_password", MT5_SERVER="test_server", POLL_INTERVAL=86401)


def test_poll_interval_validator_warning():
    cfg = TradingConfig(MT5_PASSWORD="test_password", MT5_SERVER="test_server", POLL_INTERVAL=4000)
    validator = ConfigValidator(cfg)
    result = validator.validate()

    # Should have a warning for POLL_INTERVAL > 3600
    warnings = [e for e in result.errors if e.field == "POLL_INTERVAL" and not e.critical]
    assert len(warnings) > 0
    assert "exceeds 1 hour" in warnings[0].message

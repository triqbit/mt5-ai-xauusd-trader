"""
Tests for ConfigValidator.
"""
import pytest
import os
from unittest.mock import MagicMock, patch
from pathlib import Path
from src.core.config import TradingConfig
from src.core.config_validator import ConfigValidator

@pytest.fixture
def mock_config():
    config = MagicMock(spec=TradingConfig)
    config.mt5_login = 123456
    config.mt5_password = "top_secret_prod_pass"
    config.mt5_server = "Broker-Server"
    config.mode = "demo"
    config.is_live = False
    config.risk_per_trade = 0.01
    config.max_daily_loss = 0.05
    config.model_path = MagicMock(spec=Path)
    config.model_path.exists.return_value = True
    config.database_url = "sqlite:///trades.db"
    return config

def test_validator_pass(mock_config):
    validator = ConfigValidator(mock_config)
    is_valid, errors = validator.validate()
    assert is_valid is True
    assert len(errors) == 0

def test_validator_fail_mt5_login(mock_config):
    mock_config.mt5_login = 0
    mock_config.mt5_password = "top_secret_prod_pass"
    validator = ConfigValidator(mock_config)
    is_valid, errors = validator.validate()
    assert is_valid is False
    assert any("MT5_LOGIN" in e for e in errors)

def test_validator_fail_placeholder_password(mock_config):
    mock_config.mt5_password = "your_password"
    validator = ConfigValidator(mock_config)
    is_valid, errors = validator.validate()
    assert is_valid is False
    assert any("MT5_PASSWORD" in e for e in errors)

def test_validator_fail_live_no_confirm(mock_config):
    mock_config.mode = "live"
    mock_config.is_live = True
    with patch.dict(os.environ, {"CONFIRM_LIVE_TRADING": "NO"}):
        validator = ConfigValidator(mock_config)
        is_valid, errors = validator.validate()
        assert is_valid is False
        assert any("LIVE trading mode" in e for e in errors)

def test_validator_pass_live_with_confirm(mock_config):
    mock_config.mode = "live"
    mock_config.is_live = True
    with patch.dict(os.environ, {"CONFIRM_LIVE_TRADING": "YES"}):
        validator = ConfigValidator(mock_config)
        is_valid, errors = validator.validate()
        assert is_valid is True

def test_validator_fail_risk_limits(mock_config):
    mock_config.risk_per_trade = 0.05
    validator = ConfigValidator(mock_config)
    is_valid, errors = validator.validate()
    assert is_valid is False
    assert any("risk_per_trade" in e for e in errors)

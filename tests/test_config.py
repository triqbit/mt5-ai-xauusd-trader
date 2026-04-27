import pytest
import os
from src.core.config import TradingConfig, get_config
from pydantic import ValidationError

def test_config_defaults():
    """Test that default configuration values are correctly set."""
    # We must provide some required fields if we don't have a .env
    config = TradingConfig(mt5_password="test", mt5_server="test")
    assert config.symbol == "XAUUSD"
    assert config.risk_per_trade == 0.01
    assert config.max_positions == 5

def test_config_env_vars(monkeypatch):
    """Test that environment variables override defaults."""
    monkeypatch.setenv("MT5_LOGIN", "12345")
    monkeypatch.setenv("MT5_PASSWORD", "secret")
    monkeypatch.setenv("MT5_SERVER", "BrokerServer")
    monkeypatch.setenv("MODE", "live")

    config = TradingConfig()
    assert config.mt5_login == 12345
    assert config.mt5_password == "secret"
    assert config.mode == "live"

def test_risk_validation():
    """Test that risk_per_trade > 2% raises a validation error."""
    # Pydantic's 'le=0.02' validation takes precedence over field_validator
    with pytest.raises(ValidationError):
        TradingConfig(mt5_password="test", mt5_server="test", risk_per_trade=0.05)

def test_singleton_config(monkeypatch):
    """Test that get_config returns a singleton (cached) instance."""
    monkeypatch.setenv("MT5_PASSWORD", "test")
    monkeypatch.setenv("MT5_SERVER", "test")

    cfg1 = get_config()
    cfg2 = get_config()
    assert cfg1 is cfg2

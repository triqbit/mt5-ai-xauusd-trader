"""Tests for src.core.config_validator module."""
import os
import pytest
from src.core.config import TradingConfig
from src.core.config_validator import ConfigValidator

@pytest.fixture
def base_config(monkeypatch):
    """Provides a valid base configuration for testing."""
    monkeypatch.setenv("MT5_LOGIN", "123456")
    monkeypatch.setenv("MT5_PASSWORD", "securepassword")
    monkeypatch.setenv("MT5_SERVER", "Broker-Demo")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@host:5432/db")
    return TradingConfig()

def test_validator_success(base_config):
    """Test validator succeeds with valid configuration."""
    validator = ConfigValidator(base_config)
    result = validator.validate()
    assert result.success is True
    assert len(result.errors) == 0

def test_validator_mt5_login_invalid(monkeypatch):
    """Test validator fails with invalid MT5 login."""
    monkeypatch.setenv("MT5_LOGIN", "0")
    monkeypatch.setenv("MT5_PASSWORD", "pass")
    monkeypatch.setenv("MT5_SERVER", "server")
    cfg = TradingConfig()
    validator = ConfigValidator(cfg)
    result = validator.validate()
    assert result.success is False
    assert any(e.field == "MT5_LOGIN" for e in result.errors)

def test_validator_mt5_placeholders(monkeypatch):
    """Test validator fails with placeholder MT5 server/password."""
    monkeypatch.setenv("MT5_LOGIN", "12345")
    monkeypatch.setenv("MT5_PASSWORD", "password")
    monkeypatch.setenv("MT5_SERVER", "server_name")
    cfg = TradingConfig()
    validator = ConfigValidator(cfg)
    result = validator.validate()
    assert result.success is False
    assert any(e.field == "MT5_SERVER" for e in result.errors)
    assert any(e.field == "MT5_PASSWORD" for e in result.errors)

def test_validator_live_mode_no_confirmation(monkeypatch):
    """Test validator fails in LIVE mode without CONFIRM_LIVE_TRADING=YES."""
    monkeypatch.setenv("MT5_LOGIN", "12345")
    monkeypatch.setenv("MT5_PASSWORD", "secure")
    monkeypatch.setenv("MT5_SERVER", "Broker-Live")
    monkeypatch.setenv("MODE", "live")
    monkeypatch.setenv("CONFIRM_LIVE_TRADING", "NO")

    cfg = TradingConfig()
    validator = ConfigValidator(cfg)
    result = validator.validate()
    assert result.success is False
    assert any(e.field == "MODE" and "CONFIRM_LIVE_TRADING" in e.message for e in result.errors)

def test_validator_live_mode_with_confirmation(monkeypatch):
    """Test validator succeeds in LIVE mode with confirmation."""
    monkeypatch.setenv("MT5_LOGIN", "12345")
    monkeypatch.setenv("MT5_PASSWORD", "secure")
    monkeypatch.setenv("MT5_SERVER", "Broker-Live")
    monkeypatch.setenv("MODE", "live")
    monkeypatch.setenv("CONFIRM_LIVE_TRADING", "YES")
    monkeypatch.setenv("DATABASE_URL", "postgresql://real:pass@host/db")

    cfg = TradingConfig()
    validator = ConfigValidator(cfg)
    result = validator.validate()
    assert result.success is True

def test_validator_placeholder_secrets(monkeypatch):
    """Test validator detects placeholder database URL."""
    monkeypatch.setenv("MT5_LOGIN", "12345")
    monkeypatch.setenv("MT5_PASSWORD", "secure")
    monkeypatch.setenv("MT5_SERVER", "Broker")
    monkeypatch.setenv("DATABASE_URL", "postgresql://trader:password@localhost:5432/mt5_trades")

    cfg = TradingConfig()
    validator = ConfigValidator(cfg)
    result = validator.validate()
    assert result.success is False
    assert any(e.field == "DATABASE_URL" for e in result.errors)

def test_validator_risk_parameters(monkeypatch):
    """Test validator detects unsafe risk parameters."""
    monkeypatch.setenv("MT5_LOGIN", "12345")
    monkeypatch.setenv("MT5_PASSWORD", "secure")
    monkeypatch.setenv("MT5_SERVER", "Broker")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@host:5432/db")
    monkeypatch.setenv("MAX_DAILY_LOSS", "0.16") # 16% is > 15% limit in validator

    cfg = TradingConfig()
    validator = ConfigValidator(cfg)
    result = validator.validate()
    assert result.success is False
    assert any(e.field == "MAX_DAILY_LOSS" for e in result.errors)

def test_validator_incompatible_live_positions(monkeypatch):
    """Test validator detects too many positions in LIVE mode."""
    monkeypatch.setenv("MT5_LOGIN", "12345")
    monkeypatch.setenv("MT5_PASSWORD", "secure")
    monkeypatch.setenv("MT5_SERVER", "Broker-Live")
    monkeypatch.setenv("MODE", "live")
    monkeypatch.setenv("CONFIRM_LIVE_TRADING", "YES")
    monkeypatch.setenv("MAX_POSITIONS", "10")
    monkeypatch.setenv("DATABASE_URL", "postgresql://real:pass@host/db")

    cfg = TradingConfig()
    validator = ConfigValidator(cfg)
    result = validator.validate()
    assert result.success is False
    assert any(e.field == "MAX_POSITIONS" for e in result.errors)

def test_validator_backtest_warning(monkeypatch):
    """Test validator gives a non-critical warning for Telegram in backtest."""
    monkeypatch.setenv("MT5_LOGIN", "12345")
    monkeypatch.setenv("MT5_PASSWORD", "secure")
    monkeypatch.setenv("MT5_SERVER", "Broker")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@host:5432/db")
    monkeypatch.setenv("MODE", "backtest")
    monkeypatch.setenv("TELEGRAM_TOKEN", "123:ABC")

    cfg = TradingConfig()
    validator = ConfigValidator(cfg)
    result = validator.validate()
    # It should still be successful because it's non-critical
    assert result.success is True
    assert any(e.field == "TELEGRAM_TOKEN" and e.critical is False for e in result.errors)

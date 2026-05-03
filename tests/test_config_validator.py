"""Tests for src.core.config_validator module."""
import os
import sys
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
    monkeypatch.setenv("MT5_PASSWORD", "your_password_here")
    monkeypatch.setenv("MT5_SERVER", "your_server_here")
    cfg = TradingConfig()
    validator = ConfigValidator(cfg)
    result = validator.validate()
    assert result.success is False
    assert any(e.field == "MT5_SERVER" for e in result.errors)
    assert any(e.field == "MT5_PASSWORD" for e in result.errors)

def test_validator_mt5_path_windows(monkeypatch):
    """Test validator checks MT5 path on Windows."""
    if sys.platform != "win32":
        pytest.skip("Windows-only test")

    monkeypatch.setenv("MT5_LOGIN", "12345")
    monkeypatch.setenv("MT5_PASSWORD", "pass")
    monkeypatch.setenv("MT5_SERVER", "server")
    monkeypatch.setenv("MT5_PATH", "C:/non_existent_path.exe")
    cfg = TradingConfig()
    validator = ConfigValidator(cfg)
    result = validator.validate()
    assert result.success is False
    assert any(e.field == "MT5_PATH" for e in result.errors)

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
    """Test validator detects placeholder database URL, Telegram, and MetaAPI."""
    monkeypatch.setenv("MT5_LOGIN", "12345")
    monkeypatch.setenv("MT5_PASSWORD", "secure")
    monkeypatch.setenv("MT5_SERVER", "Broker")
    monkeypatch.setenv("DATABASE_URL", "postgresql://trader:password@localhost:5432/mt5_trades")
    monkeypatch.setenv("TELEGRAM_TOKEN", "YOUR_TOKEN_HERE")
    monkeypatch.setenv("METAAPI_TOKEN", "CHANGE_ME")

    cfg = TradingConfig()
    validator = ConfigValidator(cfg)
    result = validator.validate()
    assert result.success is False
    assert any(e.field == "DATABASE_URL" for e in result.errors)
    assert any(e.field == "TELEGRAM_TOKEN" for e in result.errors)
    assert any(e.field == "METAAPI_TOKEN" for e in result.errors)

def test_validator_risk_parameters(monkeypatch):
    """Test validator detects unsafe risk parameters."""
    monkeypatch.setenv("MT5_LOGIN", "12345")
    monkeypatch.setenv("MT5_PASSWORD", "secure")
    monkeypatch.setenv("MT5_SERVER", "Broker")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@host:5432/db")

    # 1. Critical risk breach (> 2%)
    # Note: Pydantic field_validator might catch this first if we instantiate TradingConfig
    # but let's test the validator's logic.
    monkeypatch.setenv("RISK_PER_TRADE", "0.03")
    try:
        cfg = TradingConfig()
    except ValueError:
        # Pydantic already caught it, which is also fine.
        return

    validator = ConfigValidator(cfg)
    result = validator.validate()
    assert result.success is False
    assert any(e.field == "RISK_PER_TRADE" and e.critical for e in result.errors)

def test_validator_risk_warnings(monkeypatch):
    """Test validator gives warnings for risk parameters exceeding policy but not hard limits."""
    monkeypatch.setenv("MT5_LOGIN", "12345")
    monkeypatch.setenv("MT5_PASSWORD", "secure")
    monkeypatch.setenv("MT5_SERVER", "Broker")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@host:5432/db")

    # Policy limit is 1%, Warning if > 1%
    monkeypatch.setenv("RISK_PER_TRADE", "0.015")
    cfg = TradingConfig()
    validator = ConfigValidator(cfg)
    result = validator.validate()
    assert result.success is True
    assert any(e.field == "RISK_PER_TRADE" and not e.critical for e in result.errors)

def test_validator_max_daily_loss(monkeypatch):
    """Test validator detects unsafe daily loss limits."""
    monkeypatch.setenv("MT5_LOGIN", "12345")
    monkeypatch.setenv("MT5_PASSWORD", "secure")
    monkeypatch.setenv("MT5_SERVER", "Broker")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@host:5432/db")

    # Hard stop is 6%
    monkeypatch.setenv("MAX_DAILY_LOSS", "0.07")
    cfg = TradingConfig()
    validator = ConfigValidator(cfg)
    result = validator.validate()
    assert result.success is False
    assert any(e.field == "MAX_DAILY_LOSS" and e.critical for e in result.errors)

    # Warning if > 5% (Emergency Stop)
    monkeypatch.setenv("MAX_DAILY_LOSS", "0.055")
    cfg = TradingConfig()
    validator = ConfigValidator(cfg)
    result = validator.validate()
    assert result.success is True
    assert any(e.field == "MAX_DAILY_LOSS" and not e.critical for e in result.errors)

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
    assert any(e.field == "MAX_POSITIONS" and e.critical for e in result.errors)

def test_validator_backtest_warning(monkeypatch):
    """Test validator gives a non-critical warning for Telegram in backtest."""
    monkeypatch.setenv("MT5_LOGIN", "12345")
    monkeypatch.setenv("MT5_PASSWORD", "secure")
    monkeypatch.setenv("MT5_SERVER", "Broker")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@host:5432/db")
    monkeypatch.setenv("MODE", "backtest")
    monkeypatch.setenv("TELEGRAM_TOKEN", "123:ABC")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "12345")

    cfg = TradingConfig()
    validator = ConfigValidator(cfg)
    result = validator.validate()
    # It should still be successful because it's non-critical
    assert result.success is True
    assert any(e.field == "TELEGRAM_TOKEN" and e.critical is False for e in result.errors)

def test_validator_metaapi_consistency(monkeypatch):
    """Test validator detects inconsistent MetaAPI configuration."""
    monkeypatch.setenv("MT5_LOGIN", "12345")
    monkeypatch.setenv("MT5_PASSWORD", "secure")
    monkeypatch.setenv("MT5_SERVER", "Broker")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@host/db")

    # Token but no account ID
    monkeypatch.setenv("METAAPI_TOKEN", "real_token")
    cfg = TradingConfig()
    result = ConfigValidator(cfg).validate()
    assert result.success is False
    assert any(e.field == "METAAPI_ACCOUNT_ID" for e in result.errors)

    # Account ID but no token
    monkeypatch.setenv("MT5_LOGIN", "12345")
    monkeypatch.setenv("MT5_PASSWORD", "secure")
    monkeypatch.setenv("MT5_SERVER", "Broker")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@host/db")
    monkeypatch.delenv("METAAPI_TOKEN", raising=False)
    monkeypatch.setenv("METAAPI_ACCOUNT_ID", "real_id")
    cfg = TradingConfig()
    result = ConfigValidator(cfg).validate()
    assert result.success is False
    assert any(e.field == "METAAPI_TOKEN" for e in result.errors)

def test_validator_telegram_consistency(monkeypatch):
    """Test validator detects inconsistent Telegram configuration."""
    monkeypatch.setenv("MT5_LOGIN", "12345")
    monkeypatch.setenv("MT5_PASSWORD", "secure")
    monkeypatch.setenv("MT5_SERVER", "Broker")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@host/db")

    # Token but no chat ID
    monkeypatch.setenv("TELEGRAM_TOKEN", "real_token")
    cfg = TradingConfig()
    result = ConfigValidator(cfg).validate()
    assert result.success is False
    assert any(e.field == "TELEGRAM_CHAT_ID" for e in result.errors)

    # Chat ID but no token
    monkeypatch.delenv("TELEGRAM_TOKEN", raising=False)
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "12345")
    cfg = TradingConfig()
    result = ConfigValidator(cfg).validate()
    assert result.success is False
    assert any(e.field == "TELEGRAM_TOKEN" for e in result.errors)

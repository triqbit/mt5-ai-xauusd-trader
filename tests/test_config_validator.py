"""Unit tests for src.core.config_validator."""
import os
import pytest
from src.core.config import TradingConfig
from src.core.config_validator import validate_config, ValidationSeverity

@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    """Ensure environment is clean before each test."""
    monkeypatch.delenv("RISK_PER_TRADE", raising=False)
    monkeypatch.delenv("MAX_DAILY_LOSS", raising=False)
    monkeypatch.delenv("MT5_LOGIN", raising=False)
    monkeypatch.delenv("MT5_PASSWORD", raising=False)
    monkeypatch.delenv("MT5_SERVER", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("MT5_LOGIN", "123456")
    monkeypatch.setenv("MT5_PASSWORD", "secure_pass")
    monkeypatch.setenv("MT5_SERVER", "Broker-Live")
    monkeypatch.setenv("MODE", "demo")
    # Set a secure-looking DB URL by default to avoid the default password check in LIVE tests
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:secure_pass@localhost/db")

def test_validate_valid_config():
    """Test that a standard valid config passes validation."""
    cfg = TradingConfig()
    result = validate_config(cfg)
    assert result.is_valid is True
    assert len(result.issues) == 0

def test_validate_invalid_mt5_login(monkeypatch):
    monkeypatch.setenv("MT5_LOGIN", "0")
    cfg = TradingConfig()
    result = validate_config(cfg)
    assert result.is_valid is False
    assert any(i.field == "mt5_login" and i.severity == ValidationSeverity.CRITICAL for i in result.issues)

def test_validate_mt5_placeholder_password(monkeypatch):
    monkeypatch.setenv("MT5_PASSWORD", "CHANGE_ME")
    cfg = TradingConfig()
    result = validate_config(cfg)
    assert result.is_valid is False
    assert any(i.field == "mt5_password" and i.severity == ValidationSeverity.CRITICAL for i in result.issues)

def test_validate_live_mode_no_confirmation(monkeypatch):
    monkeypatch.setenv("MODE", "live")
    monkeypatch.setenv("CONFIRM_LIVE_TRADING", "NO")
    cfg = TradingConfig()
    result = validate_config(cfg)
    assert result.is_valid is False
    assert any(i.field == "mode" and "confirmation" in i.message for i in result.issues)

def test_validate_live_mode_confirmed(monkeypatch):
    monkeypatch.setenv("MODE", "live")
    monkeypatch.setenv("CONFIRM_LIVE_TRADING", "YES")
    monkeypatch.setenv("RISK_PER_TRADE", "0.01")
    cfg = TradingConfig()
    result = validate_config(cfg)
    assert result.has_critical is False

def test_validate_live_unsafe_risk(monkeypatch):
    monkeypatch.setenv("MODE", "live")
    monkeypatch.setenv("CONFIRM_LIVE_TRADING", "YES")
    monkeypatch.setenv("RISK_PER_TRADE", "0.015") # 1.5% is allowed, 0.0151+ is blocked
    cfg = TradingConfig()
    result = validate_config(cfg)
    assert result.has_critical is False

    monkeypatch.setenv("RISK_PER_TRADE", "0.016")
    cfg = TradingConfig()
    result = validate_config(cfg)
    assert result.is_valid is False
    assert any(i.field == "risk_per_trade" and i.severity == ValidationSeverity.CRITICAL for i in result.issues)

def test_validate_db_default_password_live(monkeypatch):
    monkeypatch.setenv("MODE", "live")
    monkeypatch.setenv("CONFIRM_LIVE_TRADING", "YES")
    # Reset to default or use explicit placeholder
    monkeypatch.setenv("DATABASE_URL", "postgresql://trader:password@localhost/db")
    cfg = TradingConfig()
    result = validate_config(cfg)
    assert result.is_valid is False
    assert any(i.field == "database_url" and i.severity == ValidationSeverity.CRITICAL for i in result.issues)

def test_validate_telegram_placeholder_warning(monkeypatch):
    monkeypatch.setenv("TELEGRAM_TOKEN", "your_token_here")
    cfg = TradingConfig()
    result = validate_config(cfg)
    assert result.is_valid is True
    assert any(i.field == "telegram_token" and i.severity == ValidationSeverity.WARNING for i in result.issues)

def test_validate_unsafe_daily_loss_warning(monkeypatch):
    monkeypatch.setenv("MAX_DAILY_LOSS", "0.16")
    cfg = TradingConfig()
    result = validate_config(cfg)
    assert result.is_valid is True
    assert any(i.field == "max_daily_loss" and i.severity == ValidationSeverity.WARNING for i in result.issues)

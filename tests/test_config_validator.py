"""Tests for src.core.config_validator module."""
import pytest
from src.core.config import TradingConfig
from src.core.config_validator import ConfigValidator


def test_valid_config():
    """Test that a valid config passes validation."""
    cfg = TradingConfig(
        mt5_login=12345,
        mt5_password="StrongSecret123!",
        mt5_server="Broker-Live",
        mode="demo",
        database_url="postgresql://user:other_pass@db:5432/trading"
    )
    result = ConfigValidator.validate(cfg)
    assert result.is_valid is True
    assert len(result.errors) == 0


def test_invalid_mt5_login():
    """Test validation fails with invalid MT5 login."""
    cfg = TradingConfig(
        mt5_login=0,
        mt5_password="StrongSecret123!",
        mt5_server="Broker-Live",
        database_url="postgresql://user:other_pass@db:5432/trading"
    )
    result = ConfigValidator.validate(cfg)
    assert result.is_valid is False
    assert any(i.field == "mt5_login" for i in result.errors)


def test_placeholder_mt5_credentials():
    """Test validation fails with placeholder MT5 credentials."""
    cfg = TradingConfig(
        mt5_login=12345,
        mt5_password="password",
        mt5_server="default"
    )
    result = ConfigValidator.validate(cfg)
    assert result.is_valid is False
    assert any(i.field == "mt5_password" for i in result.errors)
    assert any(i.field == "mt5_server" for i in result.errors)


def test_live_mode_without_confirmation():
    """Test live mode requires explicit confirmation."""
    cfg = TradingConfig(
        mt5_login=12345,
        mt5_password="StrongSecret123!",
        mt5_server="Broker-Live",
        mode="live",
        confirm_live_trading=False,
        database_url="postgresql://user:other_pass@db:5432/trading"
    )
    result = ConfigValidator.validate(cfg)
    assert result.is_valid is False
    assert any(i.field == "confirm_live_trading" for i in result.errors)


def test_live_mode_with_demo_server():
    """Test live mode fails if server name contains 'demo'."""
    cfg = TradingConfig(
        mt5_login=12345,
        mt5_password="StrongSecret123!",
        mt5_server="Broker-Demo-Server",
        mode="live",
        confirm_live_trading=True,
        database_url="postgresql://user:other_pass@db:5432/trading"
    )
    result = ConfigValidator.validate(cfg)
    assert result.is_valid is False
    assert any("demo" in i.message.lower() for i in result.errors)


def test_risk_parameter_validation():
    """Test validation of risk-related parameters."""
    # Risk per trade > 2% is already blocked by Pydantic field_validator,
    # but we test our validator's reinforcement of it if we bypass it or
    # if it's set to exactly 2.01% (though Pydantic will likely catch it first).

    cfg = TradingConfig(
        mt5_login=12345,
        mt5_password="StrongSecret123!",
        mt5_server="Broker-Live",
        max_daily_loss=0.15,
        max_positions=6,
        database_url="postgresql://user:other_pass@db:5432/trading"
    )
    result = ConfigValidator.validate(cfg)
    # Warnings don't make the config invalid
    assert result.is_valid is True
    assert any(i.field == "max_daily_loss" and i.level == "WARNING" for i in result.issues)
    assert any(i.field == "max_positions" and i.level == "WARNING" for i in result.issues)


def test_database_url_placeholder():
    """Test validation fails with default database credentials."""
    cfg = TradingConfig(
        mt5_login=12345,
        mt5_password="StrongSecret123!",
        mt5_server="Broker-Live",
        database_url="postgresql://trader:password@localhost:5432/mt5_trades"
    )
    result = ConfigValidator.validate(cfg)
    assert result.is_valid is False
    assert any(i.field == "database_url" for i in result.errors)

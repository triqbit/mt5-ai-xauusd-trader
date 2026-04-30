"""Tests for src.core.config_validator module."""
import os
import pytest
from src.core.config import TradingConfig
from src.core.config_validator import ConfigValidator, ValidationLevel

@pytest.fixture
def base_cfg_dict():
    return {
        "MT5_LOGIN": "12345",
        "MT5_PASSWORD": "securepassword",
        "MT5_SERVER": "RealServer",
        "MODE": "demo",
        "RISK_PER_TRADE": "0.01",
        "MAX_DAILY_LOSS": "0.05",
    }

def test_validator_valid_config(base_cfg_dict, monkeypatch):
    for k, v in base_cfg_dict.items():
        monkeypatch.setenv(k, v)

    cfg = TradingConfig()
    validator = ConfigValidator()
    result = validator.validate(cfg)

    assert result.is_valid
    assert len(result.issues) == 0

def test_validator_invalid_login(base_cfg_dict, monkeypatch):
    base_cfg_dict["MT5_LOGIN"] = "0"
    for k, v in base_cfg_dict.items():
        monkeypatch.setenv(k, v)

    cfg = TradingConfig()
    validator = ConfigValidator()
    result = validator.validate(cfg)

    assert not result.is_valid
    assert any(i.field == "mt5_login" and i.level == ValidationLevel.ERROR for i in result.issues)

def test_validator_placeholder_password(base_cfg_dict, monkeypatch):
    base_cfg_dict["MT5_PASSWORD"] = "CHANGE_ME"
    for k, v in base_cfg_dict.items():
        monkeypatch.setenv(k, v)

    cfg = TradingConfig()
    validator = ConfigValidator()
    result = validator.validate(cfg)

    assert not result.is_valid
    assert any("password" in i.field and i.level == ValidationLevel.ERROR for i in result.issues)

def test_validator_live_mode_no_confirmation(base_cfg_dict, monkeypatch):
    base_cfg_dict["MODE"] = "live"
    # Ensure confirmation is NOT set
    monkeypatch.delenv("CONFIRM_LIVE_TRADING", raising=False)
    for k, v in base_cfg_dict.items():
        monkeypatch.setenv(k, v)

    cfg = TradingConfig()
    validator = ConfigValidator()
    result = validator.validate(cfg)

    assert not result.is_valid
    assert any(i.field == "mode" and "CONFIRM_LIVE_TRADING" in i.message for i in result.issues)

def test_validator_live_mode_with_confirmation(base_cfg_dict, monkeypatch):
    base_cfg_dict["MODE"] = "live"
    monkeypatch.setenv("CONFIRM_LIVE_TRADING", "YES")
    for k, v in base_cfg_dict.items():
        monkeypatch.setenv(k, v)

    cfg = TradingConfig()
    validator = ConfigValidator()
    result = validator.validate(cfg)

    # Might still fail if MT5_SERVER contains "demo" by default in some setups,
    # but here base_cfg_dict has "RealServer"
    assert result.is_valid

def test_validator_live_mode_demo_server(base_cfg_dict, monkeypatch):
    base_cfg_dict["MODE"] = "live"
    base_cfg_dict["MT5_SERVER"] = "MetaQuotes-Demo"
    monkeypatch.setenv("CONFIRM_LIVE_TRADING", "YES")
    for k, v in base_cfg_dict.items():
        monkeypatch.setenv(k, v)

    cfg = TradingConfig()
    validator = ConfigValidator()
    result = validator.validate(cfg)

    assert not result.is_valid
    assert any(i.field == "mt5_server" and "demo" in i.message.lower() for i in result.issues)

def test_validator_risk_limits(base_cfg_dict, monkeypatch):
    # Over 1% risk
    base_cfg_dict["RISK_PER_TRADE"] = "0.015"
    for k, v in base_cfg_dict.items():
        monkeypatch.setenv(k, v)

    cfg = TradingConfig()
    validator = ConfigValidator()
    result = validator.validate(cfg)

    assert not result.is_valid
    assert any(i.field == "risk_per_trade" and i.level == ValidationLevel.ERROR for i in result.issues)

def test_validator_daily_loss_relation(base_cfg_dict, monkeypatch):
    # loss < risk
    # Both must be within Pydantic field constraints to even instantiate TradingConfig
    # risk_per_trade: ge=0.001, le=0.05 (but validator limits to 0.02)
    # max_daily_loss: ge=0.01, le=0.20
    base_cfg_dict["RISK_PER_TRADE"] = "0.02"
    base_cfg_dict["MAX_DAILY_LOSS"] = "0.01"
    for k, v in base_cfg_dict.items():
        monkeypatch.setenv(k, v)

    cfg = TradingConfig()
    validator = ConfigValidator()
    result = validator.validate(cfg)

    assert not result.is_valid
    assert any(i.field == "max_daily_loss" and "less than risk_per_trade" in i.message for i in result.issues)

def test_validator_daily_loss_tight_warning(base_cfg_dict, monkeypatch):
    # 1% risk, 1.5% loss (less than 2x risk)
    base_cfg_dict["RISK_PER_TRADE"] = "0.01"
    base_cfg_dict["MAX_DAILY_LOSS"] = "0.015"
    for k, v in base_cfg_dict.items():
        monkeypatch.setenv(k, v)

    cfg = TradingConfig()
    validator = ConfigValidator()
    result = validator.validate(cfg)

    assert result.is_valid # It's a warning, so valid
    assert any(i.field == "max_daily_loss" and i.level == ValidationLevel.WARNING for i in result.issues)

def test_validator_telegram_missing_chat_id(base_cfg_dict, monkeypatch):
    monkeypatch.setenv("TELEGRAM_TOKEN", "123456:ABC-DEF")
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    for k, v in base_cfg_dict.items():
        monkeypatch.setenv(k, v)

    cfg = TradingConfig()
    validator = ConfigValidator()
    result = validator.validate(cfg)

    assert any(i.field == "telegram_chat_id" and i.level == ValidationLevel.WARNING for i in result.issues)

def test_validator_placeholder_secrets(base_cfg_dict, monkeypatch):
    monkeypatch.setenv("TELEGRAM_TOKEN", "your_token")
    for k, v in base_cfg_dict.items():
        monkeypatch.setenv(k, v)

    cfg = TradingConfig()
    validator = ConfigValidator()
    result = validator.validate(cfg)

    assert not result.is_valid
    assert any(i.field == "telegram_token" and "placeholder" in i.message for i in result.issues)

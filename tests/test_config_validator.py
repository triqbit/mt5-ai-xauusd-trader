"""Tests for src.core.config_validator module."""
import sys

import pytest

from src.core.config import TradingConfig
from src.core.config_validator import ConfigValidator


@pytest.fixture
def base_config(monkeypatch, tmp_path):
    """Provides a valid base configuration for testing."""
    model_file = tmp_path / "model.pt"
    model_file.write_text("data")
    monkeypatch.setenv("MT5_LOGIN", "123456")
    monkeypatch.setenv("MT5_PASSWORD", "securepassword")
    monkeypatch.setenv("MT5_SERVER", "Broker-Demo")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@host:5432/db")
    monkeypatch.setenv("MODEL_PATH", str(model_file))
    return TradingConfig()

def test_validator_success(base_config):
    """Test validator succeeds with valid configuration."""
    validator = ConfigValidator(base_config)
    result = validator.validate()
    # It might have a warning for confidence_threshold if default is < 0.55
    # TradingConfig default is 0.6, so it should be clean.
    assert result.success is True
    assert len([e for e in result.errors if e.critical]) == 0

def test_validator_mt5_login_invalid(monkeypatch, tmp_path):
    """Test validator fails with invalid MT5 login."""
    model_file = tmp_path / "model.pt"
    model_file.write_text("data")
    monkeypatch.setenv("MT5_LOGIN", "0")
    monkeypatch.setenv("MT5_PASSWORD", "pass")
    monkeypatch.setenv("MT5_SERVER", "server")
    monkeypatch.setenv("MODEL_PATH", str(model_file))
    cfg = TradingConfig()
    validator = ConfigValidator(cfg)
    result = validator.validate()
    assert result.success is False
    assert any(e.field == "MT5_LOGIN" for e in result.errors)

def test_validator_mt5_placeholders(monkeypatch, tmp_path):
    """Test validator fails with placeholder MT5 server/password."""
    model_file = tmp_path / "model.pt"
    model_file.write_text("data")
    monkeypatch.setenv("MT5_LOGIN", "12345")
    monkeypatch.setenv("MT5_PASSWORD", "your_password_here")
    monkeypatch.setenv("MT5_SERVER", "your_server_here")
    monkeypatch.setenv("MODEL_PATH", str(model_file))
    cfg = TradingConfig()
    validator = ConfigValidator(cfg)
    result = validator.validate()
    assert result.success is False
    assert any(e.field == "MT5_SERVER" for e in result.errors)
    assert any(e.field == "MT5_PASSWORD" for e in result.errors)

def test_validator_mt5_path_windows(monkeypatch, tmp_path):
    """Test validator checks MT5 path on Windows."""
    if sys.platform != "win32":
        pytest.skip("Windows-only test")

    model_file = tmp_path / "model.pt"
    model_file.write_text("data")
    monkeypatch.setenv("MT5_LOGIN", "12345")
    monkeypatch.setenv("MT5_PASSWORD", "pass")
    monkeypatch.setenv("MT5_SERVER", "server")
    monkeypatch.setenv("MT5_PATH", "C:/non_existent_path.exe")
    monkeypatch.setenv("MODEL_PATH", str(model_file))
    cfg = TradingConfig()
    validator = ConfigValidator(cfg)
    result = validator.validate()
    assert result.success is False
    assert any(e.field == "MT5_PATH" for e in result.errors)

def test_validator_live_mode_no_confirmation(monkeypatch, tmp_path):
    """Test validator fails in LIVE mode without CONFIRM_LIVE_TRADING=YES."""
    model_file = tmp_path / "model.pt"
    model_file.write_text("data")
    monkeypatch.setenv("MT5_LOGIN", "12345")
    monkeypatch.setenv("MT5_PASSWORD", "secure")
    monkeypatch.setenv("MT5_SERVER", "Broker-Live")
    monkeypatch.setenv("MODE", "live")
    monkeypatch.setenv("CONFIRM_LIVE_TRADING", "NO")
    monkeypatch.setenv("MODEL_PATH", str(model_file))

    cfg = TradingConfig()
    validator = ConfigValidator(cfg)
    result = validator.validate()
    assert result.success is False
    assert any(e.field == "MODE" and "CONFIRM_LIVE_TRADING" in e.message for e in result.errors)

def test_validator_live_mode_with_confirmation(monkeypatch, tmp_path):
    """Test validator succeeds in LIVE mode with confirmation."""
    model_file = tmp_path / "model.pt"
    model_file.write_text("data")
    monkeypatch.setenv("MT5_LOGIN", "12345")
    monkeypatch.setenv("MT5_PASSWORD", "secure")
    monkeypatch.setenv("MT5_SERVER", "Broker-Live")
    monkeypatch.setenv("MODE", "live")
    monkeypatch.setenv("CONFIRM_LIVE_TRADING", "YES")
    monkeypatch.setenv("DATABASE_URL", "postgresql://real:pass@host/db")
    monkeypatch.setenv("MODEL_PATH", str(model_file))

    cfg = TradingConfig()
    validator = ConfigValidator(cfg)
    result = validator.validate()
    assert result.success is True

def test_validator_placeholder_secrets(monkeypatch, tmp_path):
    """Test validator detects placeholder database URL, Telegram, and MetaAPI."""
    model_file = tmp_path / "model.pt"
    model_file.write_text("data")
    monkeypatch.setenv("MT5_LOGIN", "12345")
    monkeypatch.setenv("MT5_PASSWORD", "secure")
    monkeypatch.setenv("MT5_SERVER", "Broker")
    monkeypatch.setenv("DATABASE_URL", "postgresql://trader:password@localhost:5432/mt5_trades")
    monkeypatch.setenv("TELEGRAM_TOKEN", "YOUR_TOKEN_HERE")
    monkeypatch.setenv("METAAPI_TOKEN", "CHANGE_ME")
    monkeypatch.setenv("MODEL_PATH", str(model_file))

    cfg = TradingConfig()
    validator = ConfigValidator(cfg)
    result = validator.validate()
    assert result.success is False
    assert any(e.field == "DATABASE_URL" for e in result.errors)
    assert any(e.field == "TELEGRAM_TOKEN" for e in result.errors)
    assert any(e.field == "METAAPI_TOKEN" for e in result.errors)

def test_validator_risk_parameters(monkeypatch, tmp_path):
    """Test validator detects unsafe risk parameters."""
    model_file = tmp_path / "model.pt"
    model_file.write_text("data")
    monkeypatch.setenv("MT5_LOGIN", "12345")
    monkeypatch.setenv("MT5_PASSWORD", "secure")
    monkeypatch.setenv("MT5_SERVER", "Broker")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@host:5432/db")
    monkeypatch.setenv("MODEL_PATH", str(model_file))

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

def test_validator_risk_warnings(monkeypatch, tmp_path):
    """Test validator gives warnings for risk parameters exceeding policy but not hard limits."""
    model_file = tmp_path / "model.pt"
    model_file.write_text("data")
    monkeypatch.setenv("MT5_LOGIN", "12345")
    monkeypatch.setenv("MT5_PASSWORD", "secure")
    monkeypatch.setenv("MT5_SERVER", "Broker")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@host:5432/db")
    monkeypatch.setenv("MODEL_PATH", str(model_file))

    # Policy limit is 1%, Warning if > 1%
    monkeypatch.setenv("RISK_PER_TRADE", "0.015")
    cfg = TradingConfig()
    validator = ConfigValidator(cfg)
    result = validator.validate()
    assert result.success is True
    assert any(e.field == "RISK_PER_TRADE" and not e.critical for e in result.errors)

def test_validator_max_daily_loss(monkeypatch, tmp_path):
    """Test validator detects unsafe daily loss limits."""
    model_file = tmp_path / "model.pt"
    model_file.write_text("data")
    monkeypatch.setenv("MT5_LOGIN", "12345")
    monkeypatch.setenv("MT5_PASSWORD", "secure")
    monkeypatch.setenv("MT5_SERVER", "Broker")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@host:5432/db")
    monkeypatch.setenv("MODEL_PATH", str(model_file))

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

def test_validator_incompatible_live_positions(monkeypatch, tmp_path):
    """Test validator detects too many positions in LIVE mode."""
    model_file = tmp_path / "model.pt"
    model_file.write_text("data")
    monkeypatch.setenv("MT5_LOGIN", "12345")
    monkeypatch.setenv("MT5_PASSWORD", "secure")
    monkeypatch.setenv("MT5_SERVER", "Broker-Live")
    monkeypatch.setenv("MODE", "live")
    monkeypatch.setenv("CONFIRM_LIVE_TRADING", "YES")
    monkeypatch.setenv("MAX_POSITIONS", "10")
    monkeypatch.setenv("DATABASE_URL", "postgresql://real:pass@host/db")
    monkeypatch.setenv("MODEL_PATH", str(model_file))

    cfg = TradingConfig()
    validator = ConfigValidator(cfg)
    result = validator.validate()
    assert result.success is False
    assert any(e.field == "MAX_POSITIONS" and e.critical for e in result.errors)

def test_validator_backtest_warning(monkeypatch, tmp_path):
    """Test validator gives a non-critical warning for Telegram in backtest."""
    model_file = tmp_path / "model.pt"
    model_file.write_text("data")
    monkeypatch.setenv("MT5_LOGIN", "12345")
    monkeypatch.setenv("MT5_PASSWORD", "secure")
    monkeypatch.setenv("MT5_SERVER", "Broker")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@host:5432/db")
    monkeypatch.setenv("MODE", "backtest")
    monkeypatch.setenv("TELEGRAM_TOKEN", "123:ABC")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "12345")
    monkeypatch.setenv("MODEL_PATH", str(model_file))

    cfg = TradingConfig()
    validator = ConfigValidator(cfg)
    result = validator.validate()
    # It should still be successful because it's non-critical
    assert result.success is True
    assert any(e.field == "TELEGRAM_TOKEN" and e.critical is False for e in result.errors)

def test_validator_metaapi_consistency(monkeypatch, tmp_path):
    """Test validator detects inconsistent MetaAPI configuration."""
    model_file = tmp_path / "model.pt"
    model_file.write_text("data")
    monkeypatch.setenv("MT5_LOGIN", "12345")
    monkeypatch.setenv("MT5_PASSWORD", "secure")
    monkeypatch.setenv("MT5_SERVER", "Broker")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@host/db")
    monkeypatch.setenv("MODEL_PATH", str(model_file))

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

def test_validator_telegram_consistency(monkeypatch, tmp_path):
    """Test validator detects inconsistent Telegram configuration."""
    model_file = tmp_path / "model.pt"
    model_file.write_text("data")
    monkeypatch.setenv("MT5_LOGIN", "12345")
    monkeypatch.setenv("MT5_PASSWORD", "secure")
    monkeypatch.setenv("MT5_SERVER", "Broker")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@host/db")
    monkeypatch.setenv("MODEL_PATH", str(model_file))

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

def test_validator_telegram_chat_id_placeholder(monkeypatch, tmp_path):
    """Test validator detects placeholder Telegram chat ID."""
    model_file = tmp_path / "model.pt"
    model_file.write_text("data")
    monkeypatch.setenv("MT5_LOGIN", "12345")
    monkeypatch.setenv("MT5_PASSWORD", "secure")
    monkeypatch.setenv("MT5_SERVER", "Broker")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@host/db")
    monkeypatch.setenv("TELEGRAM_TOKEN", "real_token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "YOUR_CHAT_ID")
    monkeypatch.setenv("MODEL_PATH", str(model_file))

    cfg = TradingConfig()
    result = ConfigValidator(cfg).validate()
    assert result.success is False
    assert any(e.field == "TELEGRAM_CHAT_ID" for e in result.errors)

def test_validator_model_path_existence(monkeypatch, tmp_path):
    """Test validator checks for model path existence in non-backtest modes."""
    monkeypatch.setenv("MT5_LOGIN", "12345")
    monkeypatch.setenv("MT5_PASSWORD", "secure")
    monkeypatch.setenv("MT5_SERVER", "Broker")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@host/db")

    # Path does not exist
    non_existent = tmp_path / "non_existent.pt"
    monkeypatch.setenv("MODEL_PATH", str(non_existent))

    cfg = TradingConfig()
    result = ConfigValidator(cfg).validate()
    assert result.success is False
    assert any(e.field == "MODEL_PATH" for e in result.errors)

    # Path exists
    existent = tmp_path / "existent.pt"
    existent.write_text("dummy")
    monkeypatch.setenv("MODEL_PATH", str(existent))

    cfg = TradingConfig()
    result = ConfigValidator(cfg).validate()
    assert result.success is True

def test_validator_live_debug_warning(monkeypatch, tmp_path):
    """Test validator gives warning for DEBUG log level in LIVE mode."""
    # Ensure model path exists to avoid other errors
    model_file = tmp_path / "model.pt"
    model_file.write_text("data")

    monkeypatch.setenv("MT5_LOGIN", "12345")
    monkeypatch.setenv("MT5_PASSWORD", "secure")
    monkeypatch.setenv("MT5_SERVER", "Broker-Live")
    monkeypatch.setenv("DATABASE_URL", "postgresql://real:pass@host/db")
    monkeypatch.setenv("MODE", "live")
    monkeypatch.setenv("CONFIRM_LIVE_TRADING", "YES")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("MODEL_PATH", str(model_file))

    cfg = TradingConfig()
    result = ConfigValidator(cfg).validate()
    # Should still be successful because it's a warning
    assert result.success is True
    assert any(e.field == "LOG_LEVEL" and e.critical is False for e in result.errors)

def test_validator_confidence_threshold(monkeypatch, tmp_path):
    """Test validator detects unsafe confidence threshold."""
    model_file = tmp_path / "model.pt"
    model_file.write_text("data")
    monkeypatch.setenv("MT5_LOGIN", "12345")
    monkeypatch.setenv("MT5_PASSWORD", "secure")
    monkeypatch.setenv("MT5_SERVER", "Broker")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@host/db")
    monkeypatch.setenv("MODEL_PATH", str(model_file))

    # Critical breach (< 0.50)
    monkeypatch.setenv("CONFIDENCE_THRESHOLD", "0.45")
    cfg = TradingConfig()
    result = ConfigValidator(cfg).validate()
    assert result.success is False
    assert any(e.field == "CONFIDENCE_THRESHOLD" and e.critical for e in result.errors)

    # Warning (< 0.55)
    monkeypatch.setenv("CONFIDENCE_THRESHOLD", "0.52")
    cfg = TradingConfig()
    result = ConfigValidator(cfg).validate()
    assert result.success is True
    assert any(e.field == "CONFIDENCE_THRESHOLD" and not e.critical for e in result.errors)

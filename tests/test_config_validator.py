"""Tests for src.core.config_validator module."""

import sys
from pathlib import Path

import pytest
from pydantic import ValidationError as PydanticValidationError

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
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@host:5432/db_real")
    monkeypatch.setenv("MODEL_PATH", str(model_file))
    # Ensure all risk limits are within safe bounds for the base config
    monkeypatch.setenv("RISK_PER_TRADE", "0.01")
    monkeypatch.setenv("MAX_DAILY_LOSS", "0.05")
    monkeypatch.setenv("MIN_CONFIDENCE", "0.55")
    monkeypatch.setenv("MAX_POSITIONS", "5")
    monkeypatch.setenv("MAX_LEVERAGE", "10")
    monkeypatch.setenv("MAX_DRAWDOWN", "0.30")
    return TradingConfig()


def test_validator_success(base_config):
    """Test validator succeeds with valid configuration."""
    validator = ConfigValidator(base_config)
    result = validator.validate()
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


def test_validator_mt5_server_spaces_live(monkeypatch, tmp_path):
    """Test validator fails with spaces in MT5 server in LIVE mode."""
    model_file = tmp_path / "model.pt"
    model_file.write_text("data")
    monkeypatch.setenv("MT5_LOGIN", "12345")
    monkeypatch.setenv("MT5_PASSWORD", "secure")
    monkeypatch.setenv("MT5_SERVER", "IC Markets Demo")
    monkeypatch.setenv("MODE", "live")
    monkeypatch.setenv("CONFIRM_LIVE_TRADING", "YES")
    monkeypatch.setenv("MODEL_PATH", str(model_file))
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@host:5432/db")

    cfg = TradingConfig()
    result = ConfigValidator(cfg).validate()
    assert result.success is False
    assert any(e.field == "MT5_SERVER" and e.critical for e in result.errors)


def test_validator_mt5_server_spaces_demo(monkeypatch, tmp_path):
    """Test validator gives warning for spaces in MT5 server in demo mode."""
    model_file = tmp_path / "model.pt"
    model_file.write_text("data")
    monkeypatch.setenv("MT5_LOGIN", "12345")
    monkeypatch.setenv("MT5_PASSWORD", "secure")
    monkeypatch.setenv("MT5_SERVER", "IC Markets Demo")
    monkeypatch.setenv("MODE", "demo")
    monkeypatch.setenv("MODEL_PATH", str(model_file))
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@host:5432/db_real")

    cfg = TradingConfig()
    result = ConfigValidator(cfg).validate()
    assert result.success is True
    assert any(e.field == "MT5_SERVER" and not e.critical for e in result.errors)


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
    assert any(e.field == "MODE" for e in result.errors)


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
    monkeypatch.setenv("MAX_POSITIONS", "5")
    monkeypatch.setenv("RISK_PER_TRADE", "0.01")

    cfg = TradingConfig()
    validator = ConfigValidator(cfg)
    result = validator.validate()
    assert result.success is True


def test_validator_placeholder_secrets(monkeypatch, tmp_path):
    """Test validator detects placeholder database URL, Telegram, MetaAPI, and Redis."""
    model_file = tmp_path / "model.pt"
    model_file.write_text("data")
    monkeypatch.setenv("MT5_LOGIN", "12345")
    monkeypatch.setenv("MT5_PASSWORD", "secure")
    monkeypatch.setenv("MT5_SERVER", "Broker")
    monkeypatch.setenv("DATABASE_URL", "postgresql://trader:password@localhost:5432/mt5_trades")
    monkeypatch.setenv("TELEGRAM_TOKEN", "YOUR_TOKEN_HERE")
    monkeypatch.setenv("METAAPI_TOKEN", "CHANGE_ME")
    monkeypatch.setenv("REDIS_URL", "redis://YOUR_TOKEN@localhost:6379/0")
    monkeypatch.setenv("MODEL_PATH", str(model_file))

    cfg = TradingConfig()
    validator = ConfigValidator(cfg)
    result = validator.validate()
    assert result.success is False
    assert any(e.field == "DATABASE_URL" for e in result.errors)
    assert any(e.field == "TELEGRAM_TOKEN" for e in result.errors)
    assert any(e.field == "METAAPI_TOKEN" for e in result.errors)
    assert any(e.field == "REDIS_URL" for e in result.errors)


def test_validator_market_parameters(monkeypatch, tmp_path):
    """Test validator checks for valid symbol and timeframe."""
    model_file = tmp_path / "model.pt"
    model_file.write_text("data")
    monkeypatch.setenv("MT5_LOGIN", "12345")
    monkeypatch.setenv("MT5_PASSWORD", "secure")
    monkeypatch.setenv("MT5_SERVER", "Broker")
    monkeypatch.setenv("MODEL_PATH", str(model_file))
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@host:5432/db_real")

    # 1. Empty Symbol
    monkeypatch.setenv("SYMBOL", "")
    with pytest.raises(PydanticValidationError):
        TradingConfig()

    # 2. Lowercase Symbol
    monkeypatch.setenv("SYMBOL", "xauusd")
    with pytest.raises(PydanticValidationError):
        TradingConfig()

    # 3. Invalid Timeframe
    monkeypatch.setenv("SYMBOL", "XAUUSD")
    monkeypatch.setenv("TIMEFRAME", "M7")
    with pytest.raises(PydanticValidationError):
        TradingConfig()

    # 4. Valid
    monkeypatch.setenv("SYMBOL", "XAUUSD")
    monkeypatch.setenv("TIMEFRAME", "H1")
    cfg = TradingConfig()
    result = ConfigValidator(cfg).validate()
    assert result.success is True


def test_validator_risk_parameters(monkeypatch, tmp_path):
    """Test validator detects unsafe risk parameters."""
    model_file = tmp_path / "model.pt"
    model_file.write_text("data")
    monkeypatch.setenv("MT5_LOGIN", "12345")
    monkeypatch.setenv("MT5_PASSWORD", "secure")
    monkeypatch.setenv("MT5_SERVER", "Broker")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@host:5432/db")
    monkeypatch.setenv("MODEL_PATH", str(model_file))

    # Critical breach (> 1%)
    monkeypatch.setenv("RISK_PER_TRADE", "0.015")
    cfg = TradingConfig()
    validator = ConfigValidator(cfg)
    result = validator.validate()
    assert result.success is False
    assert any(e.field == "RISK_PER_TRADE" and e.critical for e in result.errors)


def test_validator_max_daily_loss(monkeypatch, tmp_path):
    """Test validator detects unsafe daily loss limits."""
    model_file = tmp_path / "model.pt"
    model_file.write_text("data")
    monkeypatch.setenv("MT5_LOGIN", "12345")
    monkeypatch.setenv("MT5_PASSWORD", "secure")
    monkeypatch.setenv("MT5_SERVER", "Broker")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@host:5432/db")
    monkeypatch.setenv("MODEL_PATH", str(model_file))

    # Critical if > 5% (Emergency Stop)
    monkeypatch.setenv("MAX_DAILY_LOSS", "0.055")
    cfg = TradingConfig()
    validator = ConfigValidator(cfg)
    result = validator.validate()
    assert result.success is False
    assert any(e.field == "MAX_DAILY_LOSS" and e.critical for e in result.errors)


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
    monkeypatch.setenv("MAX_POSITIONS", "5")
    monkeypatch.setenv("RISK_PER_TRADE", "0.01")

    cfg = TradingConfig()
    result = ConfigValidator(cfg).validate()
    # Should still be successful because it's a warning
    assert result.success is True
    assert any(e.field == "LOG_LEVEL" and e.critical is False for e in result.errors)


def test_validator_min_confidence(monkeypatch, tmp_path):
    """Test validator detects unsafe confidence threshold."""
    model_file = tmp_path / "model.pt"
    model_file.write_text("data")
    monkeypatch.setenv("MT5_LOGIN", "12345")
    monkeypatch.setenv("MT5_PASSWORD", "secure")
    monkeypatch.setenv("MT5_SERVER", "Broker")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@host:5432/db")
    monkeypatch.setenv("MODEL_PATH", str(model_file))

    # Critical breach (< 0.55)
    monkeypatch.setenv("MIN_CONFIDENCE", "0.52")
    # Note: TradingConfig has ge=0.5. Validator has < 0.55.
    cfg = TradingConfig()
    result = ConfigValidator(cfg).validate()
    assert result.success is False
    assert any(e.field == "MIN_CONFIDENCE" and e.critical for e in result.errors)


def test_validator_placeholder_server_password(monkeypatch, tmp_path):
    """Test validator detects placeholder MT5 server and password."""
    model_file = tmp_path / "model.pt"
    model_file.write_text("data")
    monkeypatch.setenv("MT5_LOGIN", "123456")
    monkeypatch.setenv("MT5_PASSWORD", "YOUR_PASSWORD_HERE")
    monkeypatch.setenv("MT5_SERVER", "YOUR_SERVER_HERE")
    monkeypatch.setenv("MODEL_PATH", str(model_file))

    cfg = TradingConfig()
    result = ConfigValidator(cfg).validate()
    assert result.success is False
    assert any(e.field == "MT5_SERVER" for e in result.errors)
    assert any(e.field == "MT5_PASSWORD" for e in result.errors)


def test_validator_leverage_limits(monkeypatch, tmp_path):
    """Test validator detects unsafe leverage."""
    model_file = tmp_path / "model.pt"
    model_file.write_text("data")
    monkeypatch.setenv("MT5_LOGIN", "123456")
    monkeypatch.setenv("MT5_PASSWORD", "secure")
    monkeypatch.setenv("MT5_SERVER", "Broker")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@host/db")
    monkeypatch.setenv("MODEL_PATH", str(model_file))

    # Critical (> 10)
    monkeypatch.setenv("MAX_LEVERAGE", "15")
    cfg = TradingConfig()
    result = ConfigValidator(cfg).validate()
    assert result.success is False
    assert any(e.field == "MAX_LEVERAGE" and e.critical for e in result.errors)


def test_validator_drawdown_limits(monkeypatch, tmp_path):
    """Test validator detects unsafe drawdown limits."""
    model_file = tmp_path / "model.pt"
    model_file.write_text("data")
    monkeypatch.setenv("MT5_LOGIN", "123456")
    monkeypatch.setenv("MT5_PASSWORD", "secure")
    monkeypatch.setenv("MT5_SERVER", "Broker")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@host/db")
    monkeypatch.setenv("MODEL_PATH", str(model_file))

    # Critical (> 30%)
    monkeypatch.setenv("MAX_DRAWDOWN", "0.35")
    cfg = TradingConfig()
    result = ConfigValidator(cfg).validate()
    assert result.success is False
    assert any(e.field == "MAX_DRAWDOWN" and e.critical for e in result.errors)


def test_validator_position_size_limits(monkeypatch, tmp_path):
    """Test validator detects unsafe position size pct."""
    model_file = tmp_path / "model.pt"
    model_file.write_text("data")
    monkeypatch.setenv("MT5_LOGIN", "123456")
    monkeypatch.setenv("MT5_PASSWORD", "secure")
    monkeypatch.setenv("MT5_SERVER", "Broker")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@host/db")
    monkeypatch.setenv("MODEL_PATH", str(model_file))

    # Critical (> 10%)
    monkeypatch.setenv("MAX_POSITION_SIZE_PCT", "0.15")
    cfg = TradingConfig()
    result = ConfigValidator(cfg).validate()
    assert result.success is False
    assert any(e.field == "MAX_POSITION_SIZE_PCT" and e.critical for e in result.errors)


def test_validator_stability_guards(monkeypatch, tmp_path):
    """Test validator detects unsafe stability guards."""
    model_file = tmp_path / "model.pt"
    model_file.write_text("data")
    monkeypatch.setenv("MT5_LOGIN", "123456")
    monkeypatch.setenv("MT5_PASSWORD", "secure")
    monkeypatch.setenv("MT5_SERVER", "Broker")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@host/db")
    monkeypatch.setenv("MODEL_PATH", str(model_file))

    # Model Accuracy Floor Critical (< 0.50)
    monkeypatch.setenv("MODEL_ACCURACY_FLOOR", "0.50")
    cfg = TradingConfig()
    cfg.model_accuracy_floor = 0.45
    result = ConfigValidator(cfg).validate()
    assert any(e.field == "MODEL_ACCURACY_FLOOR" and e.critical for e in result.errors)

    # Reset
    cfg.model_accuracy_floor = 0.55

    # Model Win Rate Floor Critical (< 0.45)
    cfg.model_win_rate_floor = 0.40
    result = ConfigValidator(cfg).validate()
    assert any(e.field == "MODEL_WIN_RATE_FLOOR" and e.critical for e in result.errors)

    # Model Drift Threshold Warning (> 0.3)
    cfg.model_win_rate_floor = 0.50
    cfg.model_drift_threshold = 0.35
    result = ConfigValidator(cfg).validate()
    assert any(e.field == "MODEL_DRIFT_THRESHOLD" and not e.critical for e in result.errors)


def test_validator_calibration_threshold_critical(monkeypatch, tmp_path):
    """Test calibration threshold exceeds 0.25 is critical."""
    model_file = tmp_path / "model.pt"
    model_file.write_text("data")
    monkeypatch.setenv("MT5_LOGIN", "123456")
    monkeypatch.setenv("MT5_PASSWORD", "secure")
    monkeypatch.setenv("MT5_SERVER", "Broker")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@host/db")
    monkeypatch.setenv("MODEL_PATH", str(model_file))

    monkeypatch.setenv("MODEL_CALIBRATION_THRESHOLD", "0.30")
    cfg = TradingConfig()
    result = ConfigValidator(cfg).validate()
    assert result.success is False
    assert any(e.field == "MODEL_CALIBRATION_THRESHOLD" and e.critical for e in result.errors)


def test_validator_sqlite_live_warning(monkeypatch, tmp_path):
    """Test validator gives warning for SQLite in LIVE mode."""
    model_file = tmp_path / "model.pt"
    model_file.write_text("data")
    monkeypatch.setenv("MT5_LOGIN", "12345")
    monkeypatch.setenv("MT5_PASSWORD", "secure")
    monkeypatch.setenv("MT5_SERVER", "Broker")
    monkeypatch.setenv("MODE", "live")
    monkeypatch.setenv("CONFIRM_LIVE_TRADING", "YES")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///trades.db")
    monkeypatch.setenv("MODEL_PATH", str(model_file))
    monkeypatch.setenv("MAX_POSITIONS", "5")
    monkeypatch.setenv("RISK_PER_TRADE", "0.01")

    cfg = TradingConfig()
    result = ConfigValidator(cfg).validate()
    assert result.success is True
    assert any(e.field == "DATABASE_URL" and not e.critical for e in result.errors)


def test_validator_mt5_server_demo_live(monkeypatch, tmp_path):
    """Test validator fails with demo server in LIVE mode."""
    model_file = tmp_path / "model.pt"
    model_file.write_text("data")
    monkeypatch.setenv("MT5_LOGIN", "12345")
    monkeypatch.setenv("MT5_PASSWORD", "secure")
    monkeypatch.setenv("MT5_SERVER", "Broker-Demo")
    monkeypatch.setenv("MODE", "live")
    monkeypatch.setenv("CONFIRM_LIVE_TRADING", "YES")
    monkeypatch.setenv("DATABASE_URL", "postgresql://real:pass@host/db")
    monkeypatch.setenv("MODEL_PATH", str(model_file))

    cfg = TradingConfig()
    result = ConfigValidator(cfg).validate()
    assert result.success is False
    assert any(e.field == "MT5_SERVER" and "Demo server" in e.message for e in result.errors)


def test_validator_daily_loss_hierarchy(monkeypatch, tmp_path):
    """Test validator detects daily loss hierarchy violations."""
    model_file = tmp_path / "model.pt"
    model_file.write_text("data")
    monkeypatch.setenv("MT5_LOGIN", "123456")
    monkeypatch.setenv("MT5_PASSWORD", "secure")
    monkeypatch.setenv("MT5_SERVER", "Broker")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@host/db")
    monkeypatch.setenv("MODEL_PATH", str(model_file))

    # L1 >= L2
    monkeypatch.setenv("DAILY_LOSS_LVL1", "0.03")
    monkeypatch.setenv("DAILY_LOSS_LVL2", "0.02")
    cfg = TradingConfig()
    result = ConfigValidator(cfg).validate()
    assert result.success is False
    assert any(e.field == "DAILY_LOSS_LVL2" for e in result.errors)


def test_validator_weekly_monthly_loss_limits(monkeypatch, tmp_path):
    """Test validator detects unsafe weekly/monthly loss limits."""
    model_file = tmp_path / "model.pt"
    model_file.write_text("data")
    monkeypatch.setenv("MT5_LOGIN", "123456")
    monkeypatch.setenv("MT5_PASSWORD", "secure")
    monkeypatch.setenv("MT5_SERVER", "Broker")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@host/db")
    monkeypatch.setenv("MODEL_PATH", str(model_file))

    # Weekly critical (> 10%)
    monkeypatch.setenv("MAX_WEEKLY_LOSS", "0.15")
    cfg = TradingConfig()
    result = ConfigValidator(cfg).validate()
    assert result.success is False
    assert any(e.field == "MAX_WEEKLY_LOSS" and e.critical for e in result.errors)

    # Monthly critical (> 15%)
    monkeypatch.setenv("MAX_WEEKLY_LOSS", "0.05")
    monkeypatch.setenv("MAX_MONTHLY_LOSS", "0.20")
    cfg = TradingConfig()
    result = ConfigValidator(cfg).validate()
    assert result.success is False
    assert any(e.field == "MAX_MONTHLY_LOSS" and e.critical for e in result.errors)


def test_validator_exposure_limits(monkeypatch, tmp_path):
    """Test validator detects unsafe exposure limits."""
    model_file = tmp_path / "model.pt"
    model_file.write_text("data")
    monkeypatch.setenv("MT5_LOGIN", "123456")
    monkeypatch.setenv("MT5_PASSWORD", "secure")
    monkeypatch.setenv("MT5_SERVER", "Broker")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@host/db")
    monkeypatch.setenv("MODEL_PATH", str(model_file))

    # Single direction critical (> 30%)
    monkeypatch.setenv("MAX_SINGLE_DIRECTION_PCT", "0.40")
    cfg = TradingConfig()
    result = ConfigValidator(cfg).validate()
    assert result.success is False
    assert any(e.field == "MAX_SINGLE_DIRECTION_PCT" and e.critical for e in result.errors)

    # Total notional critical (> 100%)
    monkeypatch.setenv("MAX_SINGLE_DIRECTION_PCT", "0.20")
    monkeypatch.setenv("MAX_TOTAL_NOTIONAL_PCT", "1.10")
    cfg = TradingConfig()
    result = ConfigValidator(cfg).validate()
    assert result.success is False
    assert any(e.field == "MAX_TOTAL_NOTIONAL_PCT" and e.critical for e in result.errors)


def test_validator_spread_hierarchy(monkeypatch, tmp_path):
    """Test validator detects spread hierarchy violations."""
    model_file = tmp_path / "model.pt"
    model_file.write_text("data")
    monkeypatch.setenv("MT5_LOGIN", "123456")
    monkeypatch.setenv("MT5_PASSWORD", "secure")
    monkeypatch.setenv("MT5_SERVER", "Broker")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@host/db")
    monkeypatch.setenv("MODEL_PATH", str(model_file))

    # Alert >= Reduce
    monkeypatch.setenv("SPREAD_ALERT_PIPS", "2.0")
    monkeypatch.setenv("SPREAD_REDUCE_PIPS", "1.5")
    cfg = TradingConfig()
    result = ConfigValidator(cfg).validate()
    assert result.success is False
    assert any(e.field == "SPREAD_REDUCE_PIPS" for e in result.errors)


def test_validator_margin_hierarchy(monkeypatch, tmp_path):
    """Test validator detects margin hierarchy violations."""
    model_file = tmp_path / "model.pt"
    model_file.write_text("data")
    monkeypatch.setenv("MT5_LOGIN", "123456")
    monkeypatch.setenv("MT5_PASSWORD", "secure")
    monkeypatch.setenv("MT5_SERVER", "Broker")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@host/db")
    monkeypatch.setenv("MODEL_PATH", str(model_file))

    # Alert >= Halt
    monkeypatch.setenv("MARGIN_ALERT_PCT", "0.85")
    monkeypatch.setenv("MARGIN_HALT_PCT", "0.80")
    cfg = TradingConfig()
    result = ConfigValidator(cfg).validate()
    assert result.success is False
    assert any(e.field == "MARGIN_HALT_PCT" for e in result.errors)


def test_validator_volatility_hierarchy(monkeypatch, tmp_path):
    """Test validator detects volatility hierarchy violations."""
    model_file = tmp_path / "model.pt"
    model_file.write_text("data")
    monkeypatch.setenv("MT5_LOGIN", "123456")
    monkeypatch.setenv("MT5_PASSWORD", "secure")
    monkeypatch.setenv("MT5_SERVER", "Broker")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@host/db")
    monkeypatch.setenv("MODEL_PATH", str(model_file))

    # High >= Very High
    monkeypatch.setenv("VOLATILITY_HIGH_THRESHOLD", "2.5")
    monkeypatch.setenv("VOLATILITY_VERY_HIGH_THRESHOLD", "2.0")
    cfg = TradingConfig()
    result = ConfigValidator(cfg).validate()
    assert result.success is False
    assert any(e.field == "VOLATILITY_VERY_HIGH_THRESHOLD" for e in result.errors)


def test_validator_max_trades_per_day(monkeypatch, tmp_path):
    """Test validator detects unsafe max trades per day."""
    model_file = tmp_path / "model.pt"
    model_file.write_text("data")
    monkeypatch.setenv("MT5_LOGIN", "123456")
    monkeypatch.setenv("MT5_PASSWORD", "secure")
    monkeypatch.setenv("MT5_SERVER", "Broker")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@host/db")
    monkeypatch.setenv("MODEL_PATH", str(model_file))

    # Exceeds institutional limit of 20
    monkeypatch.setenv("MAX_TRADES_PER_DAY", "25")
    cfg = TradingConfig()
    result = ConfigValidator(cfg).validate()
    assert result.success is False
    assert any(e.field == "MAX_TRADES_PER_DAY" and e.critical for e in result.errors)


def test_validator_min_lot_size(monkeypatch, tmp_path):
    """Test validator detects too small min lot size."""
    model_file = tmp_path / "model.pt"
    model_file.write_text("data")
    monkeypatch.setenv("MT5_LOGIN", "123456")
    monkeypatch.setenv("MT5_PASSWORD", "secure")
    monkeypatch.setenv("MT5_SERVER", "Broker")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@host/db")
    monkeypatch.setenv("MODEL_PATH", str(model_file))

    # Below 0.01
    monkeypatch.setenv("MIN_LOT_SIZE", "0.005")
    cfg = TradingConfig()
    result = ConfigValidator(cfg).validate()
    assert result.success is False
    assert any(e.field == "MIN_LOT_SIZE" and e.critical for e in result.errors)


def test_validator_file_permissions(monkeypatch, tmp_path):
    """Test validator detects insecure file permissions on Linux/Mac."""
    if sys.platform == "win32":
        pytest.skip("Linux/Mac-only test")

    import os
    import stat

    # Create a dummy .env file with insecure permissions (e.g., 666)
    env_file = tmp_path / ".env"
    env_file.write_text("MT5_PASSWORD=secure")
    os.chmod(env_file, 0o666)

    monkeypatch.setenv("MT5_LOGIN", "123456")
    monkeypatch.setenv("MT5_PASSWORD", "secure")
    monkeypatch.setenv("MT5_SERVER", "Broker")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@host/db")

    cfg = TradingConfig()
    validator = ConfigValidator(cfg)

    # Mock os.stat and Path.exists to simulate insecure permissions for .env
    original_stat = os.stat

    def mocked_stat(path, *args, **kwargs):
        if str(path).endswith(".env"):

            class MockStat:
                st_mode = stat.S_IFREG | 0o666

            return MockStat()
        return original_stat(path, *args, **kwargs)

    monkeypatch.setattr(os, "stat", mocked_stat)

    # We also mock Path.exists to ensure the validator thinks .env exists
    original_exists = Path.exists

    def mocked_exists(self):
        if self.name == ".env":
            return True
        return original_exists(self)

    monkeypatch.setattr(Path, "exists", mocked_exists)

    result = validator.validate()

    # It should give a warning (not critical)
    assert any(e.field == "FILE_PERMISSION" and ".env" in e.message for e in result.errors)
    assert all(not e.critical for e in result.errors if e.field == "FILE_PERMISSION")


def test_validator_execution_parameters(monkeypatch, tmp_path):
    """Test validator checks for slippage and latency limits."""
    model_file = tmp_path / "model.pt"
    model_file.write_text("data")
    monkeypatch.setenv("MT5_LOGIN", "123456")
    monkeypatch.setenv("MT5_PASSWORD", "secure")
    monkeypatch.setenv("MT5_SERVER", "Broker")
    monkeypatch.setenv("MODEL_PATH", str(model_file))
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@host/db")

    # 1. Slippage > 1.0
    monkeypatch.setenv("MAX_SLIPPAGE_PIPS", "1.5")
    cfg = TradingConfig()
    result = ConfigValidator(cfg).validate()
    assert result.success is False
    assert any(e.field == "MAX_SLIPPAGE_PIPS" for e in result.errors)

    # 2. Latency > 5.0
    monkeypatch.setenv("MAX_SLIPPAGE_PIPS", "0.5")
    monkeypatch.setenv("EXECUTION_LATENCY_THRESHOLD", "6.0")
    cfg = TradingConfig()
    result = ConfigValidator(cfg).validate()
    assert result.success is False
    assert any(e.field == "EXECUTION_LATENCY_THRESHOLD" for e in result.errors)


def test_validator_behavior_caps(monkeypatch, tmp_path):
    """Test validator checks for behavior-based caps."""
    model_file = tmp_path / "model.pt"
    model_file.write_text("data")
    monkeypatch.setenv("MT5_LOGIN", "123456")
    monkeypatch.setenv("MT5_PASSWORD", "secure")
    monkeypatch.setenv("MT5_SERVER", "Broker")
    monkeypatch.setenv("MODEL_PATH", str(model_file))
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@host/db")

    # 1. Daily win cap > 10%
    monkeypatch.setenv("DAILY_WIN_CAP", "0.15")
    cfg = TradingConfig()
    result = ConfigValidator(cfg).validate()
    assert result.success is False
    assert any(e.field == "DAILY_WIN_CAP" for e in result.errors)

    # 2. Losing streak > 3
    monkeypatch.setenv("DAILY_WIN_CAP", "0.05")
    monkeypatch.setenv("MAX_LOSING_STREAK", "5")
    cfg = TradingConfig()
    result = ConfigValidator(cfg).validate()
    assert result.success is False
    assert any(e.field == "MAX_LOSING_STREAK" for e in result.errors)

    # 3. Winning streak > 20
    monkeypatch.setenv("MAX_LOSING_STREAK", "3")
    monkeypatch.setenv("MAX_WINNING_STREAK", "25")
    cfg = TradingConfig()
    result = ConfigValidator(cfg).validate()
    assert result.success is False
    assert any(e.field == "MAX_WINNING_STREAK" and e.critical for e in result.errors)

    # 4. Winning streak warning (> 5)
    monkeypatch.setenv("MAX_WINNING_STREAK", "10")
    cfg = TradingConfig()
    result = ConfigValidator(cfg).validate()
    assert result.success is True
    assert any(e.field == "MAX_WINNING_STREAK" and not e.critical for e in result.errors)

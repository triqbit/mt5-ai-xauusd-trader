"""Tests for src.core.config_validator module."""
import sys
from pathlib import Path

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
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
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
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")

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
    monkeypatch.setenv("RISK_PER_TRADE", "0.03")
    try:
        cfg = TradingConfig()
    except ValueError:
        # Pydantic already caught it
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

    # Hard stop is 6%. Pydantic catches > 6%.
    monkeypatch.setenv("MAX_DAILY_LOSS", "0.07")
    with pytest.raises(Exception):
        TradingConfig()

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
    monkeypatch.setenv("MAX_POSITIONS", "6")  # Limit is 5 in LIVE mode
    monkeypatch.setenv("DATABASE_URL", "postgresql://real:pass@host/db")
    monkeypatch.setenv("MODEL_PATH", str(model_file))

    cfg = TradingConfig()
    result = ConfigValidator(cfg).validate()
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

def test_validator_min_confidence(monkeypatch, tmp_path):
    """Test validator detects unsafe confidence threshold."""
    model_file = tmp_path / "model.pt"
    model_file.write_text("data")
    monkeypatch.setenv("MT5_LOGIN", "12345")
    monkeypatch.setenv("MT5_PASSWORD", "secure")
    monkeypatch.setenv("MT5_SERVER", "Broker")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@host:5432/db")
    monkeypatch.setenv("MODEL_PATH", str(model_file))

    # Critical breach (< 0.50)
    monkeypatch.setenv("MIN_CONFIDENCE", "0.45")
    # Pydantic has ge=0.5
    with pytest.raises(Exception):
        TradingConfig()

    # Warning (< 0.55)
    monkeypatch.setenv("MIN_CONFIDENCE", "0.52")
    cfg = TradingConfig()
    result = ConfigValidator(cfg).validate()
    assert result.success is True
    assert any(e.field == "MIN_CONFIDENCE" and not e.critical for e in result.errors)

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

    # Critical (> 20)
    monkeypatch.setenv("MAX_LEVERAGE", "25")
    cfg = TradingConfig()
    result = ConfigValidator(cfg).validate()
    assert result.success is False
    assert any(e.field == "MAX_LEVERAGE" and e.critical for e in result.errors)

    # Warning (> 10)
    monkeypatch.setenv("MAX_LEVERAGE", "15")
    cfg = TradingConfig()
    result = ConfigValidator(cfg).validate()
    assert result.success is True
    assert any(e.field == "MAX_LEVERAGE" and not e.critical for e in result.errors)

def test_validator_drawdown_limits(monkeypatch, tmp_path):
    """Test validator detects unsafe drawdown limits."""
    model_file = tmp_path / "model.pt"
    model_file.write_text("data")
    monkeypatch.setenv("MT5_LOGIN", "123456")
    monkeypatch.setenv("MT5_PASSWORD", "secure")
    monkeypatch.setenv("MT5_SERVER", "Broker")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@host/db")
    monkeypatch.setenv("MODEL_PATH", str(model_file))

    # Critical (> 40%)
    monkeypatch.setenv("MAX_DRAWDOWN", "0.45")
    cfg = TradingConfig()
    result = ConfigValidator(cfg).validate()
    assert result.success is False
    assert any(e.field == "MAX_DRAWDOWN" and e.critical for e in result.errors)

    # Warning (> 30%)
    monkeypatch.setenv("MAX_DRAWDOWN", "0.35")
    cfg = TradingConfig()
    result = ConfigValidator(cfg).validate()
    assert result.success is True
    assert any(e.field == "MAX_DRAWDOWN" and not e.critical for e in result.errors)

def test_validator_position_size_limits(monkeypatch, tmp_path):
    """Test validator detects unsafe position size pct."""
    model_file = tmp_path / "model.pt"
    model_file.write_text("data")
    monkeypatch.setenv("MT5_LOGIN", "123456")
    monkeypatch.setenv("MT5_PASSWORD", "secure")
    monkeypatch.setenv("MT5_SERVER", "Broker")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@host/db")
    monkeypatch.setenv("MODEL_PATH", str(model_file))

    # Critical (> 20%)
    monkeypatch.setenv("MAX_POSITION_SIZE_PCT", "0.25")
    cfg = TradingConfig()
    result = ConfigValidator(cfg).validate()
    assert result.success is False
    assert any(e.field == "MAX_POSITION_SIZE_PCT" and e.critical for e in result.errors)

    # Warning (> 10%)
    monkeypatch.setenv("MAX_POSITION_SIZE_PCT", "0.15")
    cfg = TradingConfig()
    result = ConfigValidator(cfg).validate()
    assert result.success is True
    assert any(e.field == "MAX_POSITION_SIZE_PCT" and not e.critical for e in result.errors)

def test_validator_stability_guards(monkeypatch, tmp_path):
    """Test validator detects unsafe stability guards."""
    model_file = tmp_path / "model.pt"
    model_file.write_text("data")
    monkeypatch.setenv("MT5_LOGIN", "123456")
    monkeypatch.setenv("MT5_PASSWORD", "secure")
    monkeypatch.setenv("MT5_SERVER", "Broker")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@host/db")
    monkeypatch.setenv("MODEL_PATH", str(model_file))

    # Model Accuracy Floor Critical (< 0.45)
    monkeypatch.setenv("MODEL_ACCURACY_FLOOR", "0.40")
    with pytest.raises(Exception):
        TradingConfig()

    monkeypatch.setenv("MODEL_ACCURACY_FLOOR", "0.50")
    cfg = TradingConfig()
    result = ConfigValidator(cfg).validate()
    assert not any(e.field == "MODEL_ACCURACY_FLOOR" and e.critical for e in result.errors)

    # Model Win Rate Floor Critical (< 0.40)
    monkeypatch.setenv("MODEL_WIN_RATE_FLOOR", "0.35")
    with pytest.raises(Exception):
        TradingConfig()

    # Reset win rate to valid value
    monkeypatch.setenv("MODEL_WIN_RATE_FLOOR", "0.45")

    # Model Drift Threshold Warning (> 0.4)
    monkeypatch.setenv("MODEL_DRIFT_THRESHOLD", "0.45")
    cfg = TradingConfig()
    result = ConfigValidator(cfg).validate()
    assert any(e.field == "MODEL_DRIFT_THRESHOLD" and not e.critical for e in result.errors)

# --- New tests for refined rules ---

def test_validator_mt5_server_spaces_live(monkeypatch, tmp_path):
    """Test validator treats spaces in MT5 server as critical in LIVE mode."""
    model_file = tmp_path / "model.pt"
    model_file.write_text("data")
    monkeypatch.setenv("MT5_LOGIN", "123456")
    monkeypatch.setenv("MT5_PASSWORD", "secure")
    monkeypatch.setenv("MT5_SERVER", "Broker Live Server")
    monkeypatch.setenv("MODE", "live")
    monkeypatch.setenv("CONFIRM_LIVE_TRADING", "YES")
    monkeypatch.setenv("MODEL_PATH", str(model_file))
    monkeypatch.setenv("DATABASE_URL", "postgresql://real:pass@host/db")

    cfg = TradingConfig()
    result = ConfigValidator(cfg).validate()
    assert result.success is False
    assert any(e.field == "MT5_SERVER" and e.critical for e in result.errors)

def test_validator_symbol_formatting(monkeypatch, tmp_path):
    """Test validator detects symbol issues."""
    model_file = tmp_path / "model.pt"
    model_file.write_text("data")
    monkeypatch.setenv("MT5_LOGIN", "123456")
    monkeypatch.setenv("MT5_PASSWORD", "secure")
    monkeypatch.setenv("MT5_SERVER", "Broker")
    monkeypatch.setenv("MODEL_PATH", str(model_file))
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@host/db")

    # Lowercase symbol warning
    monkeypatch.setenv("SYMBOL", "xauusd")
    cfg = TradingConfig()
    result = ConfigValidator(cfg).validate()
    assert result.success is True
    assert any(e.field == "SYMBOL" and not e.critical for e in result.errors)

    # Empty symbol critical
    monkeypatch.setenv("SYMBOL", "")
    cfg = TradingConfig()
    result = ConfigValidator(cfg).validate()
    assert result.success is False
    assert any(e.field == "SYMBOL" and e.critical for e in result.errors)

def test_validator_timeframe_validity(monkeypatch, tmp_path):
    """Test validator detects invalid timeframes."""
    model_file = tmp_path / "model.pt"
    model_file.write_text("data")
    monkeypatch.setenv("MT5_LOGIN", "123456")
    monkeypatch.setenv("MT5_PASSWORD", "secure")
    monkeypatch.setenv("MT5_SERVER", "Broker")
    monkeypatch.setenv("MODEL_PATH", str(model_file))
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@host/db")

    # Invalid timeframe
    monkeypatch.setenv("TIMEFRAME", "M155")
    cfg = TradingConfig()
    result = ConfigValidator(cfg).validate()
    assert result.success is False
    assert any(e.field == "TIMEFRAME" and e.critical for e in result.errors)

def test_validator_redis_placeholder(monkeypatch, tmp_path):
    """Test validator detects redis placeholder."""
    model_file = tmp_path / "model.pt"
    model_file.write_text("data")
    monkeypatch.setenv("MT5_LOGIN", "123456")
    monkeypatch.setenv("MT5_PASSWORD", "secure")
    monkeypatch.setenv("MT5_SERVER", "Broker")
    monkeypatch.setenv("MODEL_PATH", str(model_file))
    monkeypatch.setenv("REDIS_URL", "redis://CHANGE_ME:6379/0")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@host/db")

    cfg = TradingConfig()
    result = ConfigValidator(cfg).validate()
    assert result.success is False
    assert any(e.field == "REDIS_URL" and e.critical for e in result.errors)

def test_validator_sqlite_live_warning(monkeypatch, tmp_path):
    """Test validator warns about SQLite in live mode."""
    model_file = tmp_path / "model.pt"
    model_file.write_text("data")
    monkeypatch.setenv("MT5_LOGIN", "123456")
    monkeypatch.setenv("MT5_PASSWORD", "secure")
    monkeypatch.setenv("MT5_SERVER", "Broker-Live")
    monkeypatch.setenv("MODE", "live")
    monkeypatch.setenv("CONFIRM_LIVE_TRADING", "YES")
    monkeypatch.setenv("MODEL_PATH", str(model_file))
    monkeypatch.setenv("DATABASE_URL", "sqlite:///trades.db")

    cfg = TradingConfig()
    result = ConfigValidator(cfg).validate()
    assert result.success is True
    assert any(e.field == "DATABASE_URL" and not e.critical for e in result.errors)

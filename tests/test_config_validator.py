"""Tests for src.core.config_validator module."""
import pytest

from src.core.config import TradingConfig
from src.core.config_validator import validate_config


@pytest.fixture
def base_cfg_data():
    return {
        "MT5_LOGIN": "123456",
        "MT5_PASSWORD": "ValidPassword123!",
        "MT5_SERVER": "Broker-Server",
        "DATABASE_URL": "postgresql://user:pass@localhost/db",
        "MODEL_PATH": "models/trained/ensemble_latest.pt"
    }


def test_validate_valid_config(base_cfg_data, monkeypatch, tmp_path):
    """Test that a valid configuration passes validation."""
    model_file = tmp_path / "model.pt"
    model_file.touch()

    for k, v in base_cfg_data.items():
        monkeypatch.setenv(k, v)
    monkeypatch.setenv("MODEL_PATH", str(model_file))

    cfg = TradingConfig()
    result = validate_config(cfg)
    assert result.is_valid
    assert len(result.errors) == 0


def test_validate_invalid_mt5_login(base_cfg_data, monkeypatch):
    """Test validation fails with invalid MT5 login."""
    monkeypatch.setenv("MT5_LOGIN", "0")
    for k, v in base_cfg_data.items():
        if k != "MT5_LOGIN":
            monkeypatch.setenv(k, v)

    cfg = TradingConfig()
    result = validate_config(cfg)
    assert not result.is_valid
    assert any("MT5_LOGIN" in err for err in result.errors)


def test_validate_placeholder_password(base_cfg_data, monkeypatch):
    """Test validation fails with placeholder password."""
    monkeypatch.setenv("MT5_PASSWORD", "password")
    for k, v in base_cfg_data.items():
        if k != "MT5_PASSWORD":
            monkeypatch.setenv(k, v)

    cfg = TradingConfig()
    result = validate_config(cfg)
    assert not result.is_valid
    assert any("MT5_PASSWORD" in err for err in result.errors)


def test_validate_live_mode_no_confirmation(base_cfg_data, monkeypatch):
    """Test validation fails in live mode without explicit confirmation."""
    monkeypatch.setenv("MODE", "live")
    monkeypatch.setenv("CONFIRM_LIVE_TRADING", "false")
    for k, v in base_cfg_data.items():
        monkeypatch.setenv(k, v)

    cfg = TradingConfig()
    result = validate_config(cfg)
    assert not result.is_valid
    assert any("CONFIRM_LIVE_TRADING" in err for err in result.errors)


def test_validate_live_mode_with_confirmation(base_cfg_data, monkeypatch, tmp_path):
    """Test validation passes in live mode with explicit confirmation."""
    model_file = tmp_path / "model.pt"
    model_file.touch()

    monkeypatch.setenv("MODE", "live")
    monkeypatch.setenv("CONFIRM_LIVE_TRADING", "true")
    for k, v in base_cfg_data.items():
        monkeypatch.setenv(k, v)
    monkeypatch.setenv("MODEL_PATH", str(model_file))

    cfg = TradingConfig()
    result = validate_config(cfg)
    assert result.is_valid


def test_validate_incompatible_live_sqlite(base_cfg_data, monkeypatch, tmp_path):
    """Test warning when live mode uses SQLite."""
    model_file = tmp_path / "model.pt"
    model_file.touch()

    monkeypatch.setenv("MODE", "live")
    monkeypatch.setenv("CONFIRM_LIVE_TRADING", "true")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")
    for k, v in base_cfg_data.items():
        if k != "DATABASE_URL":
            monkeypatch.setenv(k, v)
    monkeypatch.setenv("MODEL_PATH", str(model_file))

    cfg = TradingConfig()
    result = validate_config(cfg)
    assert result.is_valid  # Still valid, but with warning
    assert any("SQLite" in warn for warn in result.warnings)


def test_validate_high_risk_params(base_cfg_data, monkeypatch, tmp_path):
    """Test warnings for high risk parameters."""
    model_file = tmp_path / "model.pt"
    model_file.touch()

    monkeypatch.setenv("MAX_DAILY_LOSS", "0.15")
    for k, v in base_cfg_data.items():
        monkeypatch.setenv(k, v)
    monkeypatch.setenv("MODEL_PATH", str(model_file))

    cfg = TradingConfig()
    result = validate_config(cfg)
    assert result.is_valid
    assert any("max_daily_loss" in warn for warn in result.warnings)


def test_validate_missing_model(base_cfg_data, monkeypatch):
    """Test validation fails if model path does not exist."""
    monkeypatch.setenv("MODEL_PATH", "non_existent_model.pt")
    for k, v in base_cfg_data.items():
        if k != "MODEL_PATH":
            monkeypatch.setenv(k, v)

    cfg = TradingConfig()
    result = validate_config(cfg)
    assert not result.is_valid
    assert any("Model path does not exist" in err for err in result.errors)

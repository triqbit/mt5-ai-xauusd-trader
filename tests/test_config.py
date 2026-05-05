"""Tests for src.core.config module."""
from unittest.mock import patch

import pytest

from src.core.config import TradingConfig, get_config


def test_config_from_env(monkeypatch):
    """Test TradingConfig loads from environment variables."""
    monkeypatch.setenv("MT5_LOGIN", "12345")
    monkeypatch.setenv("MT5_PASSWORD", "testpass")
    monkeypatch.setenv("MT5_SERVER", "TestServer-Demo")
    monkeypatch.setenv("MODE", "demo")

    cfg = TradingConfig()
    assert cfg.mt5_login == 12345
    assert cfg.mt5_password.get_secret_value() == "testpass"
    assert cfg.mt5_server == "TestServer-Demo"
    assert cfg.mode == "demo"


def test_config_defaults(monkeypatch):
    """Test TradingConfig has sensible defaults."""
    monkeypatch.setenv("MT5_LOGIN", "0")
    monkeypatch.setenv("MT5_PASSWORD", "test")
    monkeypatch.setenv("MT5_SERVER", "test")
    cfg = TradingConfig()
    assert cfg.symbol == "XAUUSD"
    assert cfg.mode == "demo"
    assert cfg.algorithm == "ensemble"


def test_config_risk_validation(monkeypatch):
    """Test risk_per_trade validation rejects unsafe values."""
    monkeypatch.setenv("MT5_LOGIN", "0")
    monkeypatch.setenv("MT5_PASSWORD", "test")
    monkeypatch.setenv("MT5_SERVER", "test")
    monkeypatch.setenv("RISK_PER_TRADE", "0.03")  # 3% - should fail
    with pytest.raises(ValueError, match="risk_per_trade"):
        TradingConfig()


def test_config_load_defaults():
    cfg = TradingConfig(MT5_PASSWORD="test", MT5_SERVER="test")
    assert cfg.symbol == "XAUUSD"
    assert cfg.max_positions == 5
    assert cfg.risk_per_trade == 0.01


def test_config_validation():
    with pytest.raises(ValueError):
        TradingConfig(MT5_PASSWORD="test", MT5_SERVER="test", risk_per_trade=0.05)


def test_singleton():
    with patch.dict("os.environ", {"MT5_PASSWORD": "test", "MT5_SERVER": "test"}):
        get_config.cache_clear()
        cfg1 = get_config()
        cfg2 = get_config()
        assert cfg1 is cfg2
        assert cfg1.mt5_server == "test"


def test_risk_params():
    cfg = TradingConfig(MT5_PASSWORD="test", MT5_SERVER="test")
    assert cfg.max_daily_loss == 0.05
    assert cfg.volatility_high_threshold == 1.5

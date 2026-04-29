"""Tests for src.core.config module."""
import os
import pytest
from src.core.config import TradingConfig

def test_config_from_env(monkeypatch):
    """Test TradingConfig loads from environment variables."""
    monkeypatch.setenv("MT5_LOGIN", "12345")
    monkeypatch.setenv("MT5_PASSWORD", "testpass")
    monkeypatch.setenv("MT5_SERVER", "TestServer-Demo")
    monkeypatch.setenv("MODE", "demo")

    cfg = TradingConfig()
    assert cfg.mt5_login == 12345
    assert cfg.mt5_password == "testpass"
    assert cfg.mt5_server == "TestServer-Demo"
    assert cfg.mode == "demo"

def test_config_defaults():
    """Test TradingConfig has sensible defaults."""
    os.environ.update({
        "MT5_LOGIN": "0",
        "MT5_PASSWORD": "test",
        "MT5_SERVER": "test",
    })
    cfg = TradingConfig()
    assert cfg.symbol == "XAUUSD"
    assert cfg.mode == "demo"
    assert cfg.algorithm == "ensemble"

def test_config_risk_validation():
    """Test risk_per_trade validation rejects unsafe values."""
    os.environ.update({
        "MT5_LOGIN": "0",
        "MT5_PASSWORD": "test",
        "MT5_SERVER": "test",
        "RISK_PER_TRADE": "0.03",  # 3% - should fail
    })
    with pytest.raises(ValueError, match="risk_per_trade"):
        TradingConfig()

def test_config_risk_parameters(monkeypatch):
    """Test new risk management fields in TradingConfig."""
    monkeypatch.setenv("MT5_PASSWORD", "test")
    monkeypatch.setenv("MT5_SERVER", "test")
    monkeypatch.setenv("RISK_PER_TRADE", "0.01")
    monkeypatch.setenv("MAX_CONSECUTIVE_LOSSES", "5")
    monkeypatch.setenv("MAX_DAILY_TRADES", "20")
    monkeypatch.setenv("MIN_RISK_REWARD", "2.5")

    cfg = TradingConfig()
    assert cfg.max_consecutive_losses == 5
    assert cfg.max_daily_trades == 20
    assert cfg.min_risk_reward == 2.5

def test_config_timeframe_validation(monkeypatch):
    """Test timeframe Literal validation."""
    monkeypatch.setenv("MT5_PASSWORD", "test")
    monkeypatch.setenv("MT5_SERVER", "test")
    monkeypatch.setenv("RISK_PER_TRADE", "0.01")

    # Valid timeframe
    monkeypatch.setenv("TIMEFRAME", "H1")
    cfg = TradingConfig()
    assert cfg.timeframe == "H1"

    # Invalid timeframe
    monkeypatch.setenv("TIMEFRAME", "M2")
    with pytest.raises(ValueError):
        TradingConfig()

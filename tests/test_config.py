"""Tests for src.core.config module."""
import pytest
from src.core.config import TradingConfig

def test_config_from_env(monkeypatch):
    """Test TradingConfig loads from environment variables."""
    monkeypatch.setenv("MT5_LOGIN", "12345")
    monkeypatch.setenv("MT5_PASSWORD", "testpass")
    monkeypatch.setenv("MT5_SERVER", "TestServer-Demo")
    monkeypatch.setenv("MODE", "demo")
    monkeypatch.setenv("SYMBOL", "XAUUSD")
    monkeypatch.setenv("RISK_PER_TRADE", "0.01")

    cfg = TradingConfig()
    assert cfg.mt5_login == 12345
    assert cfg.mt5_password == "testpass"
    assert cfg.mt5_server == "TestServer-Demo"
    assert cfg.mode == "demo"
    assert cfg.symbol == "XAUUSD"

def test_config_defaults(monkeypatch):
    """Test TradingConfig has sensible defaults."""
    monkeypatch.setenv("MT5_LOGIN", "0")
    monkeypatch.setenv("MT5_PASSWORD", "test")
    monkeypatch.setenv("MT5_SERVER", "test")
    monkeypatch.setenv("RISK_PER_TRADE", "0.01")

    cfg = TradingConfig()
    assert cfg.symbol == "XAUUSD"
    assert cfg.mode == "demo"
    assert cfg.algorithm == "ensemble"
    assert cfg.max_positions == 5
    assert cfg.max_position_size_pct == 0.10

def test_config_risk_validation(monkeypatch):
    """Test risk_per_trade validation rejects unsafe values."""
    monkeypatch.setenv("MT5_LOGIN", "0")
    monkeypatch.setenv("MT5_PASSWORD", "test")
    monkeypatch.setenv("MT5_SERVER", "test")
    monkeypatch.setenv("RISK_PER_TRADE", "0.03")  # 3% - should fail

    with pytest.raises(ValueError, match="risk_per_trade"):
        TradingConfig()

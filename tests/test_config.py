"""Tests for src.core.config module."""
import os
import pytest
from src.core.config import TradingConfig

@pytest.fixture(autouse=True)
def clean_env():
    """Ensure a clean environment for each test."""
    original_env = os.environ.copy()
    # Remove relevant env vars
    vars_to_remove = ["MT5_LOGIN", "MT5_PASSWORD", "MT5_SERVER", "MODE", "RISK_PER_TRADE"]
    for var in vars_to_remove:
        if var in os.environ:
            del os.environ[var]
    yield
    os.environ.clear()
    os.environ.update(original_env)

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

def test_config_defaults(monkeypatch):
    """Test TradingConfig has sensible defaults."""
    monkeypatch.setenv("MT5_LOGIN", "0")
    monkeypatch.setenv("MT5_PASSWORD", "test")
    monkeypatch.setenv("MT5_SERVER", "test")

    cfg = TradingConfig()
    assert cfg.symbol == "XAUUSD"
    assert cfg.mode == "demo"
    assert cfg.algorithm == "ensemble"
    assert cfg.max_positions == 5
    assert cfg.max_leverage == 10
    assert cfg.max_trades_per_day == 20

def test_config_risk_validation(monkeypatch):
    """Test risk_per_trade validation rejects unsafe values."""
    monkeypatch.setenv("MT5_LOGIN", "0")
    monkeypatch.setenv("MT5_PASSWORD", "test")
    monkeypatch.setenv("MT5_SERVER", "test")
    monkeypatch.setenv("RISK_PER_TRADE", "0.03")  # 3% - should fail

    with pytest.raises(ValueError, match="risk_per_trade"):
        TradingConfig()

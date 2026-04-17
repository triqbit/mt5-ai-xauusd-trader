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

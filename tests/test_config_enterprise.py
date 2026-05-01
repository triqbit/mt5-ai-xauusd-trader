import pytest
import os
from src.core.config import get_config, TradingConfig

def test_trading_config_defaults():
    # Set env vars to avoid validation errors if they are required
    os.environ["MT5_LOGIN"] = "123456"
    os.environ["MT5_PASSWORD"] = "secret"
    os.environ["MT5_SERVER"] = "Broker-Server"

    config = get_config()
    assert config.mt5_login == 123456
    assert config.symbol == "XAUUSD"
    assert config.risk_per_trade == 0.01
    assert "hard" in config.daily_loss_levels
    assert config.daily_loss_levels["hard"] == 0.06
    assert config.consensus_threshold == 0.60

from pydantic import ValidationError

def test_risk_must_be_safe_validator():
    with pytest.raises(ValidationError):
        TradingConfig(
            mt5_login=1,
            mt5_password="p",
            mt5_server="s",
            risk_per_trade=0.03
        )

def test_drawdown_levels():
    config = get_config()
    assert config.drawdown_levels["5"] == 0.30
    assert config.drawdown_levels["1"] == 0.10

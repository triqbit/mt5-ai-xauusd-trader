from unittest.mock import patch

import pytest

from src.core.config import TradingConfig, get_config


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

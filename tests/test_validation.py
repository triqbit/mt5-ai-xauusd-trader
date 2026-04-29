"""
Tests for input validation and schema enforcement.
"""
import pytest
from pydantic import ValidationError
from src.core.config import TradingConfig
from src.trading.risk_manager import TradeSignal

def test_trading_config_validation():
    """Test TradingConfig rejects invalid inputs."""
    # Invalid symbol
    with pytest.raises(ValidationError) as excinfo:
        TradingConfig(mt5_login=123, mt5_password="p", mt5_server="s", symbol="INVALID")
    assert "Symbol INVALID is not in the approved ALLOCATION_WEIGHTS portfolio" in str(excinfo.value)

    # Invalid timeframe
    with pytest.raises(ValidationError) as excinfo:
        TradingConfig(mt5_login=123, mt5_password="p", mt5_server="s", timeframe="M2")
    assert "Input should be 'M1', 'M5', 'M15', 'M30', 'H1', 'H4' or 'D1'" in str(excinfo.value)

    # Negative mt5_login
    with pytest.raises(ValidationError) as excinfo:
        TradingConfig(mt5_login=-1, mt5_password="p", mt5_server="s")
    assert "Input should be greater than 0" in str(excinfo.value)

def test_trade_signal_validation():
    """Test TradeSignal enforces strict rules."""
    valid_params = {
        "symbol": "XAUUSD",
        "direction": 1,
        "entry_price": 2000.0,
        "stop_loss": 1990.0,
        "take_profit": 2020.0,
        "lot_size": 0.1,
        "algorithm": "test",
        "confidence": 0.8
    }

    # Valid signal
    signal = TradeSignal(**valid_params)
    assert signal.symbol == "XAUUSD"

    # Invalid direction
    with pytest.raises(ValidationError):
        TradeSignal(**{**valid_params, "direction": 0})

    # Invalid SL for BUY
    with pytest.raises(ValidationError) as excinfo:
        TradeSignal(**{**valid_params, "direction": 1, "stop_loss": 2010.0})
    assert "Stop loss must be below entry price for BUY signals" in str(excinfo.value)

    # Invalid TP for SELL
    with pytest.raises(ValidationError) as excinfo:
        TradeSignal(**{**valid_params, "direction": -1, "entry_price": 2000.0, "stop_loss": 2010.0, "take_profit": 2005.0})
    assert "Take profit must be below entry price for SELL signals" in str(excinfo.value)

    # Negative lot size
    with pytest.raises(ValidationError):
        TradeSignal(**{**valid_params, "lot_size": -0.1})

import pytest
from pydantic import ValidationError
from datetime import datetime, timezone
from src.trading.risk_manager import TradeSignal
from src.core.constants import SignalDirection

def test_valid_buy_signal():
    signal = TradeSignal(
        symbol="XAUUSD",
        direction=SignalDirection.BUY,
        entry_price=2000.0,
        stop_loss=1990.0,
        take_profit=2020.0,
        lot_size=0.1,
        algorithm="test_algo",
        confidence=0.8
    )
    assert signal.symbol == "XAUUSD"
    assert signal.direction == SignalDirection.BUY
    assert signal.entry_price == 2000.0
    assert isinstance(signal.timestamp, datetime)

def test_valid_sell_signal():
    signal = TradeSignal(
        symbol="XAUUSD",
        direction=SignalDirection.SELL,
        entry_price=2000.0,
        stop_loss=2010.0,
        take_profit=1980.0,
        lot_size=0.1,
        algorithm="test_algo",
        confidence=0.8
    )
    assert signal.direction == SignalDirection.SELL
    assert signal.stop_loss > signal.entry_price
    assert signal.take_profit < signal.entry_price

def test_invalid_negative_price():
    with pytest.raises(ValidationError):
        TradeSignal(
            symbol="XAUUSD",
            direction=SignalDirection.BUY,
            entry_price=-2000.0,
            stop_loss=1990.0,
            take_profit=2020.0,
            lot_size=0.1,
            algorithm="test_algo",
            confidence=0.8
        )

def test_invalid_confidence():
    with pytest.raises(ValidationError):
        TradeSignal(
            symbol="XAUUSD",
            direction=SignalDirection.BUY,
            entry_price=2000.0,
            stop_loss=1990.0,
            take_profit=2020.0,
            lot_size=0.1,
            algorithm="test_algo",
            confidence=1.5
        )

def test_buy_invalid_sl():
    # SL must be below entry for BUY
    with pytest.raises(ValidationError, match="Stop Loss .* must be below Entry Price"):
        TradeSignal(
            symbol="XAUUSD",
            direction=SignalDirection.BUY,
            entry_price=2000.0,
            stop_loss=2001.0,
            take_profit=2020.0,
            lot_size=0.1,
            algorithm="test_algo",
            confidence=0.8
        )

def test_buy_invalid_tp():
    # TP must be above entry for BUY
    with pytest.raises(ValidationError, match="Take Profit .* must be above Entry Price"):
        TradeSignal(
            symbol="XAUUSD",
            direction=SignalDirection.BUY,
            entry_price=2000.0,
            stop_loss=1990.0,
            take_profit=1999.0,
            lot_size=0.1,
            algorithm="test_algo",
            confidence=0.8
        )

def test_sell_invalid_sl():
    # SL must be above entry for SELL
    with pytest.raises(ValidationError, match="Stop Loss .* must be above Entry Price"):
        TradeSignal(
            symbol="XAUUSD",
            direction=SignalDirection.SELL,
            entry_price=2000.0,
            stop_loss=1999.0,
            take_profit=1980.0,
            lot_size=0.1,
            algorithm="test_algo",
            confidence=0.8
        )

def test_sell_invalid_tp():
    # TP must be below entry for SELL
    with pytest.raises(ValidationError, match="Take Profit .* must be below Entry Price"):
        TradeSignal(
            symbol="XAUUSD",
            direction=SignalDirection.SELL,
            entry_price=2000.0,
            stop_loss=2010.0,
            take_profit=2001.0,
            lot_size=0.1,
            algorithm="test_algo",
            confidence=0.8
        )

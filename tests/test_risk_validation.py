
import pytest
from pydantic import ValidationError
from src.trading.risk_manager import TradeSignal, RiskManager
from src.core.config import TradingConfig

def test_trade_signal_validation_buy_success():
    """Valid BUY signal should pass validation."""
    signal = TradeSignal(
        symbol="XAUUSD",
        direction=1,
        entry_price=2300.0,
        stop_loss=2290.0,
        take_profit=2320.0,
        lot_size=0.1,
        algorithm="ensemble",
        confidence=0.8
    )
    assert signal.direction == 1

def test_trade_signal_validation_buy_fail_sl():
    """BUY signal with SL above entry should fail."""
    with pytest.raises(ValidationError, match="Stop loss .* must be below entry"):
        TradeSignal(
            symbol="XAUUSD",
            direction=1,
            entry_price=2300.0,
            stop_loss=2310.0,
            take_profit=2320.0,
            lot_size=0.1,
            algorithm="ensemble",
            confidence=0.8
        )

def test_trade_signal_validation_sell_fail_tp():
    """SELL signal with TP above entry should fail."""
    with pytest.raises(ValidationError, match="Take profit .* must be below entry"):
        TradeSignal(
            symbol="XAUUSD",
            direction=-1,
            entry_price=2300.0,
            stop_loss=2310.0,
            take_profit=2320.0,
            lot_size=0.1,
            algorithm="ensemble",
            confidence=0.8
        )

def test_risk_manager_rejection_confidence():
    """RiskManager should reject signals with low confidence based on config."""
    cfg = TradingConfig(
        confidence_threshold=0.9, mt5_password="test", mt5_server="test"
    )
    risk = RiskManager(cfg, account_balance=10000)

    signal = TradeSignal(
        symbol="XAUUSD",
        direction=1,
        entry_price=2300.0,
        stop_loss=2290.0,
        take_profit=2320.0,
        lot_size=0.1,
        algorithm="ensemble",
        confidence=0.8  # < 0.9
    )

    assert risk.approve(signal) is False

def test_risk_manager_rejection_ensemble_dissent():
    """RiskManager should reject signals if models disagree and dissent is disallowed."""
    cfg = TradingConfig(
        ensemble_dissent_allowed=False, mt5_password="test", mt5_server="test"
    )
    risk = RiskManager(cfg, account_balance=10000)

    signal = TradeSignal(
        symbol="XAUUSD",
        direction=1,
        entry_price=2300.0,
        stop_loss=2290.0,
        take_profit=2320.0,
        lot_size=0.1,
        algorithm="ensemble",
        confidence=0.8,
        votes={"ppo": 1, "lstm": -1}  # Direct opposition
    )

    assert risk.approve(signal) is False

def test_config_symbol_validation():
    """Config should reject unsupported symbols."""
    with pytest.raises(ValidationError, match="Symbol INVALID not in supported list"):
        TradingConfig(symbol="INVALID", mt5_password="test", mt5_server="test")

def test_config_timeframe_validation():
    """Config should reject unsupported timeframes."""
    with pytest.raises(ValidationError, match="Timeframe H2 not in supported list"):
        TradingConfig(timeframe="H2", mt5_password="test", mt5_server="test")

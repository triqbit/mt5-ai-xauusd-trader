import pytest
from datetime import datetime
from pydantic import ValidationError
from src.schemas.market_data import OHLCVData
from src.schemas.signals import TradeSignal
from src.schemas.risk import RiskParameters
from src.schemas.execution import ExecutionDecision
from src.schemas.performance import PerformanceMetrics

def test_ohlcv_data_valid():
    data = {
        "time": datetime.now(),
        "open": 2000.0,
        "high": 2010.0,
        "low": 1990.0,
        "close": 2005.0,
        "tick_volume": 100
    }
    ohlcv = OHLCVData(**data)
    assert ohlcv.open == 2000.0
    assert ohlcv.tick_volume == 100

def test_ohlcv_data_invalid():
    with pytest.raises(ValidationError):
        OHLCVData(
            time=datetime.now(),
            open=2000.0,
            high=2010.0,
            low=1990.0,
            close=2005.0,
            tick_volume=-1  # Invalid: ge=0
        )

def test_trade_signal_valid():
    data = {
        "symbol": "XAUUSD",
        "direction": 1,
        "entry_price": 2000.0,
        "stop_loss": 1980.0,
        "take_profit": 2040.0,
        "lot_size": 0.1,
        "algorithm": "ensemble",
        "confidence": 0.85
    }
    signal = TradeSignal(**data)
    assert signal.symbol == "XAUUSD"
    assert signal.confidence == 0.85

def test_trade_signal_invalid_confidence():
    with pytest.raises(ValidationError):
        TradeSignal(
            symbol="XAUUSD",
            direction=1,
            entry_price=2000.0,
            stop_loss=1980.0,
            take_profit=2040.0,
            lot_size=0.1,
            algorithm="ensemble",
            confidence=1.5  # Invalid: le=1.0
        )

def test_risk_parameters_valid():
    rp = RiskParameters(max_positions=5, risk_per_trade=0.02, max_daily_loss=0.1)
    assert rp.max_positions == 5

def test_risk_parameters_invalid_risk():
    with pytest.raises(ValidationError):
        RiskParameters(risk_per_trade=0.1)  # Invalid: le=0.05

def test_execution_decision():
    signal = TradeSignal(
        symbol="XAUUSD",
        direction=1,
        entry_price=2000.0,
        stop_loss=1980.0,
        take_profit=2040.0,
        lot_size=0.1,
        algorithm="ensemble",
        confidence=0.85
    )
    decision = ExecutionDecision(approved=True, reason="Pass", signal=signal)
    assert decision.approved is True
    assert decision.signal.symbol == "XAUUSD"

def test_performance_metrics_valid():
    pm = PerformanceMetrics(
        sharpe_ratio=2.1,
        profit_factor=1.5,
        max_drawdown=500.0,
        total_trades=100,
        win_rate=0.6
    )
    assert pm.win_rate == 0.6

def test_performance_metrics_invalid_win_rate():
    with pytest.raises(ValidationError):
        PerformanceMetrics(
            sharpe_ratio=2.1,
            profit_factor=1.5,
            max_drawdown=500.0,
            total_trades=100,
            win_rate=1.1  # Invalid: le=1.0
        )
